"""Tests : statuts des comptes et CRUD des comptes dans l'admin Django."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

User = get_user_model()
PASSWORD = "MotDePasse-Test-123"


def make_user(email="user@dochub.test", role=User.Role.UTILISATEUR, **kw):
    kw.setdefault("first_name", "Test")
    kw.setdefault("last_name", "User")
    return User.objects.create_user(email=email, password=PASSWORD, role=role, **kw)


def in_days(days):
    return timezone.now() + timedelta(days=days)


# ---------------------------------------------------------------- Statuts

class StatutTests(TestCase):
    def login_session(self, email="user@dochub.test"):
        """Connexion par session (même chemin que la page de connexion de l'admin)."""
        return self.client.login(email=email, password=PASSWORD)

    def jwt(self, email="user@dochub.test"):
        return APIClient().post(reverse("users:token_obtain"), {"email": email, "password": PASSWORD},
                                format="json")

    def test_only_open_accounts_can_log_in(self):
        user = make_user()
        cases = [
            (User.Statut.OUVERT, None, True),
            (User.Statut.SUSPENDU, in_days(3), False),
            (User.Statut.BLOQUE, None, False),
            (User.Statut.FERME, None, False),
        ]
        for statut, until, allowed in cases:
            with self.subTest(statut=statut):
                user.statut, user.suspendu_jusqua = statut, until
                user.save()
                self.client.logout()
                self.assertEqual(self.login_session(), allowed)
                self.assertEqual(self.jwt().status_code, 200 if allowed else 401)

    def test_suspension_needs_a_future_end_date(self):
        user = make_user()
        user.statut = User.Statut.SUSPENDU
        with self.assertRaisesMessage(ValidationError, "Indiquez jusqu'à quand"):
            user.full_clean()
        user.suspendu_jusqua = in_days(-1)
        with self.assertRaisesMessage(ValidationError, "dans le futur"):
            user.full_clean()
        user.suspendu_jusqua = in_days(1)
        user.full_clean()  # valide

    def test_expired_suspension_is_lifted_at_login(self):
        user = make_user()
        User.objects.filter(pk=user.pk).update(statut=User.Statut.SUSPENDU, suspendu_jusqua=in_days(-1),
                                               is_active=False, motif_statut="Test")
        self.assertTrue(self.login_session())
        user.refresh_from_db()
        self.assertEqual(user.statut, User.Statut.OUVERT)
        self.assertIsNone(user.suspendu_jusqua)
        self.assertEqual(user.motif_statut, "")

    def test_expired_suspension_is_lifted_for_jwt_too(self):
        user = make_user()
        User.objects.filter(pk=user.pk).update(statut=User.Statut.SUSPENDU, suspendu_jusqua=in_days(-1),
                                               is_active=False)
        self.assertEqual(self.jwt().status_code, 200)

    def test_blocking_ends_an_open_session_and_existing_jwt(self):
        user = make_user()
        self.login_session()
        self.assertEqual(self.client.get(reverse("users:me")).status_code, 200)
        token = self.jwt().data["access"]
        user.statut = User.Statut.BLOQUE
        user.save()
        # Session déjà ouverte : la requête suivante n'est plus authentifiée
        self.assertEqual(self.client.get(reverse("users:me")).status_code, 401)
        # JWT déjà délivré : refusé
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(api.get(reverse("users:me")).status_code, 401)

    def test_leaving_suspended_status_clears_the_date_and_open_clears_the_reason(self):
        user = make_user(statut=User.Statut.SUSPENDU, suspendu_jusqua=in_days(2), motif_statut="Spam")
        user.statut = User.Statut.BLOQUE
        user.save()
        self.assertIsNone(user.suspendu_jusqua)
        self.assertEqual(user.motif_statut, "Spam")
        user.statut = User.Statut.OUVERT
        user.save()
        self.assertEqual(user.motif_statut, "")

    def test_demoting_a_superuser_removes_all_admin_rights(self):
        root = User.objects.create_superuser("root@dochub.test", PASSWORD, first_name="R", last_name="R")
        root.role = User.Role.UTILISATEUR
        root.save()
        self.assertFalse(root.is_superuser)
        self.assertFalse(root.is_staff)


# ---------------------------------------------------------------- Admin Django : accès

class AdminAccessTests(TestCase):
    changelist = reverse("admin:users_user_changelist")

    def test_anonymous_is_sent_to_admin_login(self):
        r = self.client.get(self.changelist)
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("admin:login"), r["Location"])

    def test_normal_user_cannot_enter_admin(self):
        self.client.force_login(make_user())
        r = self.client.get(self.changelist)
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("admin:login"), r["Location"])

    def test_dochub_admin_without_superuser_can_manage_users(self):
        admin_user = make_user(email="admin@dochub.test", role=User.Role.ADMIN)
        self.assertFalse(admin_user.is_superuser)
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get(self.changelist).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:users_user_add")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_groups_are_hidden(self):
        self.client.force_login(make_user(email="admin@dochub.test", role=User.Role.ADMIN))
        self.assertNotContains(self.client.get(reverse("admin:index")), "Groupes")


# ---------------------------------------------------------------- Admin Django : CRUD

class AdminCrudTests(TestCase):
    changelist = reverse("admin:users_user_changelist")
    add_url = reverse("admin:users_user_add")

    def setUp(self):
        self.admin = make_user(email="admin@dochub.test", role=User.Role.ADMIN)
        self.client.force_login(self.admin)

    def change_url(self, user):
        return reverse("admin:users_user_change", args=[user.pk])

    def change_data(self, user, **kw):
        data = {"email": user.email, "first_name": user.first_name, "last_name": user.last_name,
                "role": user.role, "statut": user.statut, "motif_statut": user.motif_statut,
                "suspendu_jusqua_0": "", "suspendu_jusqua_1": ""}
        data.update(kw)
        return data

    def add_data(self, **kw):
        data = {"first_name": "Lina", "last_name": "Bouzid", "email": "lina@dochub.test",
                "role": "UTILISATEUR", "statut": "OUVERT", "password1": "", "password2": ""}
        data.update(kw)
        return data

    # ---- Create

    def test_add_form_defaults_to_normal_user(self):
        r = self.client.get(self.add_url)
        self.assertContains(r, '<option value="UTILISATEUR" selected>')

    def test_create_normal_user_without_password_sends_activation(self):
        r = self.client.post(self.add_url, self.add_data())
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(email="lina@dochub.test")
        self.assertEqual(user.role, User.Role.UTILISATEUR)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/activer/", mail.outbox[0].body)

    def test_create_admin_with_password(self):
        r = self.client.post(self.add_url, self.add_data(role="ADMIN", password1="Un-Mdp-Solide-42",
                                                         password2="Un-Mdp-Solide-42"))
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(email="lina@dochub.test")
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("Un-Mdp-Solide-42"))
        self.assertEqual(len(mail.outbox), 0)

    def test_create_validation(self):
        cases = [
            ({"email": "admin@dochub.test"}, "Un compte existe déjà avec cette adresse email."),
            ({"email": "pas-un-email"}, "Saisissez une adresse"),
            ({"first_name": "L1na"}, "Lettres, espaces, apostrophes et tirets uniquement."),
            ({"last_name": ""}, "Ce champ est obligatoire."),
            ({"password1": "Un-Mdp-Solide-42", "password2": "autre"}, "Les deux mots de passe ne correspondent pas."),
            ({"password1": "123", "password2": "123"}, "Ce mot de passe est trop court"),
            ({"statut": "SUSPENDU"}, "Sélectionnez un choix valide"),
            ({"role": "SUPERADMIN"}, "Sélectionnez un choix valide"),
        ]
        for override, message in cases:
            with self.subTest(override=override):
                r = self.client.post(self.add_url, self.add_data(**override))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, message.replace("'", "&#x27;"))
        self.assertFalse(User.objects.filter(email="lina@dochub.test").exists())

    # ---- Read

    def test_list_search_and_filters(self):
        make_user(email="youssef@dochub.test", first_name="Youssef")
        make_user(email="bloque@dochub.test", statut=User.Statut.BLOQUE)
        r = self.client.get(self.changelist)
        self.assertContains(r, "youssef@dochub.test")
        self.assertContains(r, "bloque@dochub.test")
        r = self.client.get(self.changelist, {"q": "youssef"})
        self.assertContains(r, "youssef@dochub.test")
        self.assertNotContains(r, "bloque@dochub.test")
        r = self.client.get(self.changelist, {"statut__exact": "BLOQUE"})
        self.assertContains(r, "bloque@dochub.test")
        self.assertNotContains(r, "youssef@dochub.test")
        r = self.client.get(self.changelist, {"role__exact": "ADMIN"})
        self.assertContains(r, "admin@dochub.test")
        self.assertNotContains(r, "youssef@dochub.test")

    # ---- Update

    def test_promote_user_to_admin_and_back(self):
        user = make_user()
        self.client.post(self.change_url(user), self.change_data(user, role="ADMIN"))
        user.refresh_from_db()
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_staff)
        self.client.post(self.change_url(user), self.change_data(user, role="UTILISATEUR"))
        user.refresh_from_db()
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_staff)

    def test_edit_identity(self):
        user = make_user()
        r = self.client.post(self.change_url(user), self.change_data(user, first_name="Mariem", last_name="Kacem",
                                                                    email="Mariem.Kacem@dochub.test"))
        self.assertEqual(r.status_code, 302)
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.last_name, user.email),
                         ("Mariem", "Kacem", "mariem.kacem@dochub.test"))

    def test_edit_rejects_email_of_another_account(self):
        user = make_user()
        r = self.client.post(self.change_url(user), self.change_data(user, email="admin@dochub.test"))
        self.assertContains(r, "Un compte existe déjà avec cette adresse email.")

    def test_suspend_with_end_date(self):
        user = make_user()
        until = timezone.localtime(in_days(5))
        r = self.client.post(self.change_url(user), self.change_data(
            user, statut="SUSPENDU", motif_statut="Comportement", suspendu_jusqua_0=until.strftime("%d/%m/%Y"),
            suspendu_jusqua_1=until.strftime("%H:%M:%S")))
        self.assertEqual(r.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.statut, User.Statut.SUSPENDU)
        self.assertFalse(user.is_active)
        self.assertEqual(user.motif_statut, "Comportement")

    def test_suspend_without_or_with_past_date_is_refused(self):
        user = make_user()
        r = self.client.post(self.change_url(user), self.change_data(user, statut="SUSPENDU"))
        self.assertContains(r, "Indiquez jusqu&#x27;à quand le compte est suspendu.")
        past = timezone.localtime(in_days(-1))
        r = self.client.post(self.change_url(user), self.change_data(
            user, statut="SUSPENDU", suspendu_jusqua_0=past.strftime("%d/%m/%Y"),
            suspendu_jusqua_1=past.strftime("%H:%M:%S")))
        self.assertContains(r, "La date de fin de suspension doit être dans le futur.")
        user.refresh_from_db()
        self.assertEqual(user.statut, User.Statut.OUVERT)

    def test_block_and_close(self):
        user = make_user()
        for statut in ["BLOQUE", "FERME"]:
            with self.subTest(statut=statut):
                self.client.post(self.change_url(user), self.change_data(user, statut=statut))
                user.refresh_from_db()
                self.assertEqual(user.statut, statut)
                self.assertFalse(user.is_active)

    def test_admin_cannot_demote_or_lock_themselves(self):
        r = self.client.post(self.change_url(self.admin), self.change_data(self.admin, role="UTILISATEUR"))
        self.assertContains(r, "Vous ne pouvez pas retirer votre propre rôle d&#x27;Administrateur.")
        r = self.client.post(self.change_url(self.admin), self.change_data(self.admin, statut="FERME"))
        self.assertContains(r, "Vous ne pouvez pas suspendre, bloquer ou fermer votre propre compte.")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_admin)
        self.assertEqual(self.admin.statut, User.Statut.OUVERT)

    # ---- Delete

    def test_delete_user(self):
        user = make_user()
        r = self.client.post(reverse("admin:users_user_delete", args=[user.pk]), {"post": "yes"})
        self.assertRedirects(r, self.changelist)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_delete_another_admin(self):
        other = make_user(email="other-admin@dochub.test", role=User.Role.ADMIN)
        self.client.post(reverse("admin:users_user_delete", args=[other.pk]), {"post": "yes"})
        self.assertFalse(User.objects.filter(pk=other.pk).exists())

    def test_admin_cannot_delete_themselves(self):
        r = self.client.post(reverse("admin:users_user_delete", args=[self.admin.pk]), {"post": "yes"})
        self.assertEqual(r.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_bulk_delete_including_themselves_is_refused(self):
        user = make_user()
        self.client.post(self.changelist, {"action": "delete_selected", "post": "yes",
                                           "_selected_action": [user.pk, self.admin.pk]})
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    # ---- Actions groupées

    def run_action(self, action, *users):
        return self.client.post(self.changelist, {"action": action, "_selected_action": [u.pk for u in users]},
                                follow=True)

    def test_bulk_promote_and_demote(self):
        a, b = make_user(email="a@dochub.test"), make_user(email="b@dochub.test")
        self.run_action("promouvoir_admin", a, b)
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 3)
        r = self.run_action("retrograder_utilisateur", a, b, self.admin)
        self.assertContains(r, "Votre propre compte a été ignoré")
        self.assertEqual(list(User.objects.filter(role=User.Role.ADMIN)), [self.admin])

    def test_bulk_suspend_block_close_reopen(self):
        user = make_user()
        self.run_action("suspendre_7_jours", user, self.admin)
        user.refresh_from_db()
        self.assertEqual(user.statut, User.Statut.SUSPENDU)
        self.assertGreater(user.suspendu_jusqua, in_days(6))
        for action, statut in [("bloquer", "BLOQUE"), ("fermer", "FERME"), ("rouvrir", "OUVERT")]:
            with self.subTest(action=action):
                self.run_action(action, user, self.admin)
                user.refresh_from_db()
                self.assertEqual(user.statut, statut)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.statut, User.Statut.OUVERT)

    def test_resend_activation_only_to_pending_accounts(self):
        pending = User.objects.create_user(email="pending@dochub.test", password=None, first_name="P",
                                           last_name="P")
        active = make_user()
        r = self.run_action("renvoyer_activation", pending, active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["pending@dochub.test"])
        self.assertContains(r, "1 compte(s) ignoré(s)")
