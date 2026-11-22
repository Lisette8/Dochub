"""Tests : gestion des comptes dans les pages DocHub (/utilisateurs/)."""
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .testing import (
    NEW_PASSWORD, NOM, NOM_2, PASSWORD, PRENOM, PRENOM_2, make_email, make_name, make_password, make_short_password, make_user,
)

User = get_user_model()

LIST = reverse("users:user_list")
ADD = reverse("users:user_create")
DELETE = reverse("users:users_delete")


def edit_url(user):
    return reverse("users:user_update", args=[user.pk])


def password_url(user):
    return reverse("users:user_password", args=[user.pk])


class AccessTests(TestCase):
    def setUp(self):
        self.target = make_user(email=make_email("target"))
        self.gets = [LIST, ADD, edit_url(self.target), password_url(self.target)]

    def test_anonymous_goes_to_login(self):
        for url in self.gets:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"{reverse('users:login')}?next={url}")

    def test_normal_user_gets_403_everywhere(self):
        self.client.force_login(make_user())
        for url in self.gets:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {"action": "promouvoir_admin"}).status_code, 403)
        self.assertEqual(self.client.post(DELETE, {"comptes": self.target.pk, "confirmer": "oui"}).status_code, 403)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_admin)

    def test_menu_links(self):
        admin_url = reverse("admin:users_user_changelist")
        self.client.force_login(make_user(email=make_email("admin"), role=User.Role.ADMIN))
        r = self.client.get(reverse("users:dashboard"))
        self.assertContains(r, f'href="{LIST}"', count=2)
        self.assertNotContains(r, admin_url)
        # Le bouton « Admin Django » est seulement sur la page Utilisateurs
        self.assertContains(self.client.get(LIST), f'href="{admin_url}"', count=1)
        self.assertNotContains(self.client.get(ADD), admin_url)
        self.assertNotContains(self.client.get(edit_url(self.target)), admin_url)
        self.client.force_login(make_user())
        r = self.client.get(reverse("users:dashboard"))
        self.assertNotContains(r, LIST)
        self.assertNotContains(r, admin_url)

    def test_delete_needs_post(self):
        self.client.force_login(make_user(email=make_email("admin"), role=User.Role.ADMIN))
        self.assertEqual(self.client.get(DELETE).status_code, 405)

    def test_unknown_account_is_404(self):
        self.client.force_login(make_user(email=make_email("admin"), role=User.Role.ADMIN))
        self.assertEqual(self.client.get(reverse("users:user_update", args=[999999])).status_code, 404)


class CrudTests(TestCase):
    def setUp(self):
        self.admin = make_user(email=make_email("admin"), role=User.Role.ADMIN, last_name=make_name("a"))
        self.client.force_login(self.admin)

    def add_data(self, **kw):
        return {"first_name": PRENOM, "last_name": NOM, "email": make_email("nouveau"),
                "role": "UTILISATEUR", "statut": "OUVERT", "password1": "", "password2": "", **kw}

    def edit_data(self, user, **kw):
        return {"email": user.email, "first_name": user.first_name, "last_name": user.last_name,
                "role": user.role, "statut": user.statut, "motif_statut": user.motif_statut,
                "suspendu_jusqua": "", **kw}

    # ---- Liste

    def test_list_search_filters(self):
        make_user(email=make_email("cherche"), first_name=PRENOM_2, last_name=NOM_2)
        make_user(email=make_email("bloque"), statut=User.Statut.BLOQUE)

        def emails(**params):
            return {u.email for u in self.client.get(LIST, params).context["page"]}

        self.assertEqual(len(emails()), 3)
        self.assertEqual(emails(q=f"{PRENOM_2} {NOM_2}".lower()), {make_email("cherche")})
        self.assertEqual(emails(q="CHERCHE@"), {make_email("cherche")})
        self.assertEqual(emails(statut="BLOQUE"), {make_email("bloque")})
        self.assertEqual(emails(role="ADMIN"), {make_email("admin")})
        self.assertEqual(emails(role="ADMIN", statut="BLOQUE"), set())
        self.assertContains(self.client.get(LIST, {"q": "zzz"}), "Aucun compte ne correspond")

    def test_list_sort(self):
        other = make_user(email=make_email("b"), last_name=make_name("z"))
        names = [u.last_name for u in self.client.get(LIST, {"tri": "nom"}).context["page"]]
        self.assertEqual(names, [self.admin.last_name, other.last_name])
        names = [u.last_name for u in self.client.get(LIST, {"tri": "-nom"}).context["page"]]
        self.assertEqual(names, [other.last_name, self.admin.last_name])

    def test_list_ignores_bad_parameters(self):
        r = self.client.get(LIST, {"tri": "password", "role": "x", "statut": "x", "page": "abc", "q": "a\x00"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["params"]["tri"], "-creation")

    def test_list_pagination_keeps_filters(self):
        for i in range(settings.COMPTES_PAR_PAGE + 1):
            make_user(email=make_email(f"u{i}"))
        r = self.client.get(LIST, {"role": "UTILISATEUR"})
        self.assertEqual(len(r.context["page"]), settings.COMPTES_PAR_PAGE)
        self.assertContains(r, "?role=UTILISATEUR&amp;page=2")
        self.assertEqual(len(self.client.get(LIST, {"role": "UTILISATEUR", "page": 2}).context["page"]), 1)

    def test_names_are_escaped(self):
        User.objects.filter(pk=make_user().pk).update(first_name="<script>x</script>")
        self.assertNotContains(self.client.get(LIST), "<script>x</script>")

    # ---- Créer

    def test_add_form_defaults_to_normal_user(self):
        self.assertContains(self.client.get(ADD), '<option value="UTILISATEUR" selected>')

    def test_create_without_password_sends_activation(self):
        r = self.client.post(ADD, self.add_data(), follow=True)
        self.assertRedirects(r, LIST)
        self.assertContains(r, f"Le compte de {PRENOM} {NOM} a été créé.")
        user = User.objects.get(email=make_email("nouveau"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(mail.outbox[0].to, [make_email("nouveau")])
        log = LogEntry.objects.get(action_flag=ADDITION)
        self.assertEqual((log.user, log.object_id), (self.admin, str(user.pk)))

    def test_create_admin_with_password(self):
        self.client.post(ADD, self.add_data(role="ADMIN", password1=NEW_PASSWORD, password2=NEW_PASSWORD))
        user = User.objects.get(email=make_email("nouveau"))
        self.assertTrue(user.is_admin and user.is_staff)
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertEqual(mail.outbox, [])

    def test_create_validation(self):
        cases = [
            ({"email": make_email("ADMIN")}, "Un compte existe déjà avec cette adresse email."),
            ({"email": "pas-un-email"}, "Saisissez une adresse"),
            ({"email": ""}, "Ce champ est obligatoire."),
            ({"first_name": PRENOM + "1"}, "Lettres, espaces, apostrophes et tirets uniquement."),
            ({"last_name": ""}, "Ce champ est obligatoire."),
            ({"password1": NEW_PASSWORD, "password2": make_password()},
             "Les deux mots de passe ne correspondent pas."),
            ({"password1": (short := make_short_password()), "password2": short}, "Ce mot de passe est trop court"),
            ({"statut": "SUSPENDU"}, "Sélectionnez un choix valide"),
            ({"role": "SUPERADMIN"}, "Sélectionnez un choix valide"),
        ]
        for override, message in cases:
            with self.subTest(fields=list(override)):
                self.assertContains(self.client.post(ADD, self.add_data(**override)), message)
        self.assertFalse(User.objects.filter(email=make_email("nouveau")).exists())

    # ---- Modifier

    def test_edit_identity_and_role(self):
        user = make_user()
        r = self.client.post(edit_url(user), self.edit_data(user, first_name=PRENOM_2, role="ADMIN",
                                                            email=make_email("Modifie")))
        self.assertRedirects(r, LIST)
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.email), (PRENOM_2, make_email("modifie")))
        self.assertTrue(user.is_admin and user.is_staff)
        self.assertTrue(user.check_password(PASSWORD))  # le mot de passe n'est pas touché
        self.assertEqual(LogEntry.objects.get().action_flag, CHANGE)

    def test_edit_rejects_email_of_another_account(self):
        user = make_user()
        self.assertContains(self.client.post(edit_url(user), self.edit_data(user, email=make_email("admin"))),
                            "Un compte existe déjà avec cette adresse email.")

    def test_suspend_with_date(self):
        user = make_user()
        until = timezone.localtime(timezone.now() + timedelta(days=5))
        self.client.post(edit_url(user), self.edit_data(
            user, statut="SUSPENDU", motif_statut="Spam", suspendu_jusqua=until.strftime("%Y-%m-%dT%H:%M")))
        user.refresh_from_db()
        self.assertEqual((user.statut, user.motif_statut, user.is_active), ("SUSPENDU", "Spam", False))
        self.assertEqual(timezone.localtime(user.suspendu_jusqua).strftime("%d %H:%M"), until.strftime("%d %H:%M"))
        # La date enregistrée est réaffichée dans le champ datetime-local
        self.assertContains(self.client.get(edit_url(user)), until.strftime("%Y-%m-%dT%H:%M"))

    def test_suspend_without_or_with_past_date_is_refused(self):
        user = make_user()
        for value, message in [("", "Indiquez jusqu&#x27;à quand le compte est suspendu."),
                               ("2020-01-01T10:00", "La date de fin de suspension doit être dans le futur.")]:
            with self.subTest(value=value):
                r = self.client.post(edit_url(user), self.edit_data(user, statut="SUSPENDU", suspendu_jusqua=value))
                self.assertContains(r, message)
        user.refresh_from_db()
        self.assertEqual(user.statut, User.Statut.OUVERT)

    def test_admin_cannot_demote_or_lock_themselves(self):
        r = self.client.post(edit_url(self.admin), self.edit_data(self.admin, role="UTILISATEUR"))
        self.assertContains(r, "Vous ne pouvez pas retirer votre propre rôle")
        r = self.client.post(edit_url(self.admin), self.edit_data(self.admin, statut="BLOQUE"))
        self.assertContains(r, "Vous ne pouvez pas suspendre, bloquer ou fermer votre propre compte.")
        for action in ["retrograder_utilisateur", "suspendre", "bloquer", "fermer"]:
            self.client.post(edit_url(self.admin), {"action": action})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_admin and self.admin.is_active)

    def test_quick_actions_on_edit_page(self):
        user = make_user()
        for action, field, value in [("promouvoir_admin", "role", "ADMIN"), ("bloquer", "statut", "BLOQUE"),
                                     ("rouvrir", "statut", "OUVERT"), ("fermer", "statut", "FERME"),
                                     ("suspendre", "statut", "SUSPENDU"),
                                     ("retrograder_utilisateur", "role", "UTILISATEUR")]:
            with self.subTest(action=action):
                r = self.client.post(edit_url(user), {"action": action}, follow=True)
                self.assertRedirects(r, edit_url(user))
                user.refresh_from_db()
                self.assertEqual(getattr(user, field), value)
        self.assertContains(r, "Action : Bloquer.")  # historique affiché

    def test_unknown_action_changes_nothing(self):
        user = make_user()
        self.client.post(edit_url(user), {"action": "pirater"})
        self.client.post(LIST, {"action": "pirater", "comptes": [user.pk]})
        user.refresh_from_db()
        self.assertEqual((user.role, user.statut), ("UTILISATEUR", "OUVERT"))

    # ---- Mot de passe

    def test_set_password(self):
        user = make_user()
        r = self.client.post(password_url(user), {"usable_password": "true", "password1": NEW_PASSWORD,
                                                  "password2": NEW_PASSWORD})
        self.assertRedirects(r, edit_url(user))
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))

    def test_password_validation(self):
        user = make_user()
        short = make_short_password()
        for p1, p2, message in [("", "", "Le mot de passe est obligatoire."),
                                (NEW_PASSWORD, make_password(), "Les deux mots de passe ne correspondent pas."),
                                (short, short, "Ce mot de passe est trop court")]:
            with self.subTest(message=message):
                self.assertContains(self.client.post(password_url(user), {
                    "usable_password": "true", "password1": p1, "password2": p2}), message)
        user.refresh_from_db()
        self.assertTrue(user.check_password(PASSWORD))

    def test_remove_password_sends_activation(self):
        user = make_user()
        self.client.post(password_url(user), {"usable_password": "false", "password1": "", "password2": ""})
        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())
        self.assertIn("/activer/", mail.outbox[0].body)

    def test_own_password_keeps_session_and_cannot_be_removed(self):
        self.client.post(password_url(self.admin), {"usable_password": "false", "password1": "", "password2": ""})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.has_usable_password())
        self.client.post(password_url(self.admin), {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(NEW_PASSWORD))
        self.assertEqual(self.client.get(LIST).status_code, 200)  # toujours connecté

    # ---- Supprimer

    def test_delete_asks_for_confirmation_first(self):
        user = make_user()
        r = self.client.post(DELETE, {"comptes": [user.pk]})
        self.assertContains(r, "Oui, supprimer")
        self.assertContains(r, user.email)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        r = self.client.post(DELETE, {"comptes": [user.pk], "confirmer": "oui"}, follow=True)
        self.assertContains(r, "1 compte(s) supprimé(s).")
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertEqual(LogEntry.objects.get().action_flag, DELETION)

    def test_bulk_delete_skips_own_account(self):
        a, b = make_user(email=make_email("a")), make_user(email=make_email("b"))
        ids = [a.pk, b.pk, self.admin.pk]
        r = self.client.post(LIST, {"action": "supprimer", "comptes": ids})
        self.assertContains(r, "Supprimer 2 comptes ?")
        self.client.post(DELETE, {"comptes": ids, "confirmer": "oui"})
        self.assertEqual(list(User.objects.all()), [self.admin])

    def test_delete_own_account_is_refused(self):
        r = self.client.post(DELETE, {"comptes": [self.admin.pk], "confirmer": "oui"}, follow=True)
        self.assertContains(r, "Votre propre compte a été ignoré")
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_delete_with_bad_ids(self):
        r = self.client.post(DELETE, {"comptes": ["abc", "-1", "9" * 40], "confirmer": "oui"}, follow=True)
        self.assertContains(r, "Aucun compte à supprimer.")

    def test_confirmation_lists_linked_data(self):
        other = make_user(email=make_email("other"), role=User.Role.ADMIN)
        LogEntry.objects.log_actions(other.pk, [self.admin], CHANGE, "x")
        self.assertContains(self.client.post(DELETE, {"comptes": [other.pk]}), "Seront aussi supprimés")

    # ---- Actions groupées

    def bulk(self, action, *users):
        return self.client.post(LIST, {"action": action, "comptes": [u.pk for u in users]}, follow=True)

    def test_bulk_actions(self):
        a, b = make_user(email=make_email("a")), make_user(email=make_email("b"))
        for action, field, value in [("promouvoir_admin", "role", "ADMIN"),
                                     ("retrograder_utilisateur", "role", "UTILISATEUR"),
                                     ("suspendre", "statut", "SUSPENDU"), ("bloquer", "statut", "BLOQUE"),
                                     ("fermer", "statut", "FERME"), ("rouvrir", "statut", "OUVERT")]:
            with self.subTest(action=action):
                self.assertContains(self.bulk(action, a, b), "2 compte(s)")
                for user in (a, b):
                    user.refresh_from_db()
                    self.assertEqual(getattr(user, field), value)

    def test_bulk_action_skips_own_account(self):
        user = make_user()
        r = self.bulk("bloquer", user, self.admin)
        self.assertContains(r, "Votre propre compte a été ignoré")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_bulk_without_selection_or_action(self):
        self.assertContains(self.bulk("bloquer"), "Cochez au moins un compte.")
        self.assertContains(self.bulk("", make_user()), "Choisissez une action.")

    def test_bulk_resend_activation(self):
        pending = User.objects.create_user(email=make_email("p"), password=None, first_name=make_name(), last_name=make_name())
        r = self.bulk("renvoyer_activation", pending, make_user())
        self.assertEqual([m.to for m in mail.outbox], [[make_email("p")]])
        self.assertContains(r, "1 compte(s) ignoré(s)")

    def test_bulk_action_keeps_filters(self):
        user = make_user()
        url = LIST + "?role=UTILISATEUR&page=1"
        self.assertRedirects(self.client.post(url, {"action": "bloquer", "comptes": [user.pk]}), url)
