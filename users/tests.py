import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .testing import (
    NEW_PASSWORD, NOM, NOM_2, PASSWORD, PRENOM, PRENOM_2, make_email, make_name, make_password, make_short_password, make_user,
)

User = get_user_model()


class UserModelTests(TestCase):
    def test_email_is_normalized_and_role_defaults_to_user(self):
        u = make_user(email=make_email("Someone").upper())
        self.assertEqual(u.email, make_email("someone"))
        self.assertEqual(u.role, User.Role.UTILISATEUR)
        self.assertFalse(u.is_admin)
        self.assertFalse(u.is_staff)

    def test_admin_role_gives_staff_access(self):
        u = make_user(role=User.Role.ADMIN)
        self.assertTrue(u.is_admin)
        self.assertTrue(u.is_staff)

    def test_superuser_is_admin(self):
        u = User.objects.create_superuser(make_email("root"), PASSWORD, first_name=make_name(), last_name=make_name())
        self.assertTrue(u.is_admin)


class LoginPageTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def post_login(self, email, password):
        return self.client.post(reverse("users:login"), {"username": email, "password": password})

    def test_login_success_redirects_to_dashboard(self):
        r = self.post_login(make_email("user"), PASSWORD)
        self.assertRedirects(r, reverse("users:dashboard"))

    def test_login_is_case_insensitive_on_email(self):
        r = self.post_login(make_email().upper(), PASSWORD)
        self.assertRedirects(r, reverse("users:dashboard"))

    def test_wrong_password_shows_error(self):
        r = self.post_login(make_email("user"), make_password())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Email ou mot de passe incorrect")

    def test_invalid_email_and_empty_fields_are_rejected(self):
        r = self.post_login("pas-un-email", PASSWORD)
        self.assertContains(r, "Saisissez une adresse email valide.")
        r = self.post_login("", "")
        self.assertContains(r, "L&#x27;adresse email est obligatoire.")
        self.assertContains(r, "Le mot de passe est obligatoire.")

    def test_deactivated_account_cannot_log_in(self):
        self.user.statut = User.Statut.BLOQUE
        self.user.save()
        r = self.post_login(make_email("user"), PASSWORD)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_page_uses_mockup_template(self):
        r = self.client.get(reverse("users:login"))
        self.assertTemplateUsed(r, "users/login.html")
        self.assertContains(r, "Se souvenir de moi")
        self.assertContains(r, "css/dochub.css")

    def test_session_persists_across_requests(self):
        self.post_login(make_email("user"), PASSWORD)
        self.assertEqual(self.client.get(reverse("users:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("users:dashboard")).status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_without_remember_me_session_ends_with_browser(self):
        self.post_login(make_email("user"), PASSWORD)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_with_remember_me_session_is_kept(self):
        self.client.post(reverse("users:login"),
                         {"username": make_email("user"), "password": PASSWORD, "remember_me": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_logout(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("users:logout"))
        self.assertRedirects(r, reverse("users:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class PagePermissionTests(TestCase):
    changelist = reverse("admin:users_user_changelist")

    def test_anonymous_is_redirected_to_login(self):
        r = self.client.get(reverse("users:dashboard"))
        self.assertRedirects(r, reverse("users:login") + "?next=/")

    def test_old_administration_url_opens_django_admin(self):
        self.client.force_login(make_user(role=User.Role.ADMIN))
        r = self.client.get(reverse("users:admin_space"))
        self.assertRedirects(r, self.changelist)

    def test_sidebar_and_dashboard_link_to_users_page_for_admins_only(self):
        users_page = reverse("users:user_list")
        self.client.force_login(make_user(email=make_email("a"), role=User.Role.ADMIN))
        r = self.client.get(reverse("users:dashboard"))
        self.assertContains(r, f'href="{users_page}"', count=2)  # menu + carte Administration
        self.client.force_login(make_user())
        self.assertNotContains(self.client.get(reverse("users:dashboard")), users_page)

    def test_user_cannot_open_django_admin(self):
        self.client.force_login(make_user())
        r = self.client.get(self.changelist)
        self.assertRedirects(r, reverse("admin:login") + "?next=" + self.changelist)

    def test_logged_in_pages_are_never_cached(self):
        self.client.force_login(make_user(role=User.Role.ADMIN))
        for url in [reverse("users:dashboard"), self.changelist]:
            cc = self.client.get(url)["Cache-Control"]
            self.assertIn("no-store", cc)
            self.assertIn("private", cc)

    def test_back_button_after_switching_account_shows_no_admin_page(self):
        # Admin connecté -> déconnexion -> connexion en tant qu'utilisateur
        self.client.force_login(make_user(email=make_email("a"), role=User.Role.ADMIN))
        self.client.post(reverse("users:logout"))
        self.client.force_login(make_user())
        # Le navigateur redemande la page (no-store) : la session actuelle s'applique
        self.assertEqual(self.client.get(self.changelist).status_code, 302)


class JWTTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = make_user()

    def test_obtain_token_and_access_protected_route(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": make_email("user"), "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)

        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        me = self.api.get(reverse("users:me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], make_email("user"))
        self.assertEqual(me.data["role"], "UTILISATEUR")

    def test_protected_route_without_token_is_refused(self):
        self.assertEqual(self.api.get(reverse("users:me")).status_code, 401)

    def test_email_is_case_insensitive(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": f" {make_email().upper()} ", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_wrong_credentials_give_401(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": make_email("user"), "password": make_password()}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_deactivated_account_gets_no_token(self):
        self.user.statut = User.Statut.BLOQUE
        self.user.save()
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": make_email("user"), "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_refresh_token(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": make_email("user"), "password": PASSWORD}, format="json")
        r2 = self.api.post(reverse("users:token_refresh"), {"refresh": r.data["refresh"]}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access", r2.data)


class RegisterTests(TestCase):
    url = reverse("users:register")

    def data(self, **kw):
        d = {"first_name": PRENOM, "last_name": NOM, "email": make_email("Nouveau.Compte"),
             "password1": NEW_PASSWORD, "password2": NEW_PASSWORD}
        d.update(kw)
        return d

    def test_register_creates_user_account_and_logs_in(self):
        r = self.client.post(self.url, self.data())
        self.assertRedirects(r, reverse("users:dashboard"))
        u = User.objects.get(email=make_email("nouveau.compte"))
        self.assertEqual(u.role, User.Role.UTILISATEUR)
        self.assertTrue(u.is_active)
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.pk)

    def test_register_cannot_choose_admin_role(self):
        self.client.post(self.url, self.data(role="ADMIN"))
        self.assertFalse(User.objects.get(email=make_email("nouveau.compte")).is_admin)

    def test_register_validation(self):
        make_user(email=make_email("pris"))
        cases = [
            ({"email": make_email("pris")}, "Un compte existe déjà avec cette adresse email."),
            ({"email": "pas-un-email"}, "Saisissez une adresse email valide."),
            ({"first_name": ""}, "Ce champ est obligatoire."),
            ({"last_name": NOM + "0!"}, "Lettres, espaces, apostrophes et tirets uniquement."),
            ({"password2": make_password()}, "Les deux mots de passe ne correspondent pas."),
            ({"password1": (short := make_short_password()), "password2": short}, "Ce mot de passe est trop court"),
        ]
        for override, message in cases:
            with self.subTest(override=override):
                r = self.client.post(self.url, self.data(**override))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, message.replace("'", "&#x27;"))
        self.assertFalse(User.objects.filter(email=make_email("nouveau.compte")).exists())

    def test_login_page_links_to_register(self):
        self.assertContains(self.client.get(reverse("users:login")), self.url)


class ActivationTests(TestCase):
    """Compte créé par un admin (admin Django) -> lien d'activation -> connexion sur DocHub."""

    def setUp(self):
        self.client.force_login(make_user(email=make_email("admin"), role=User.Role.ADMIN))
        self.client.post(reverse("admin:users_user_add"), {
            "first_name": PRENOM_2, "last_name": NOM_2, "email": make_email("cherche"),
            "role": "UTILISATEUR", "statut": "OUVERT", "password1": "", "password2": ""})
        self.client.post(reverse("users:logout"))
        self.link = re.search(r"http://testserver(/activer/\S+)", mail.outbox[0].body).group(1)

    def test_activation_link_sets_password_then_user_can_log_in(self):
        r = self.client.get(self.link, follow=True)  # Django redirige vers une URL sans le jeton
        self.assertTemplateUsed(r, "users/activate.html")
        form_url = r.redirect_chain[-1][0]
        r = self.client.post(form_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})
        self.assertRedirects(r, reverse("users:login"))
        r = self.client.post(reverse("users:login"), {"username": make_email("cherche"), "password": NEW_PASSWORD})
        self.assertRedirects(r, reverse("users:dashboard"))
        # Le lien ne fonctionne qu'une fois
        self.client.post(reverse("users:logout"))
        self.assertContains(self.client.get(self.link, follow=True), "Lien invalide")

    def test_activation_form_validation(self):
        form_url = self.client.get(self.link, follow=True).redirect_chain[-1][0]
        r = self.client.post(form_url, {"new_password1": NEW_PASSWORD, "new_password2": make_password()})
        self.assertContains(r, "Les deux mots de passe ne correspondent pas.")
        r = self.client.post(form_url, {"new_password1": "", "new_password2": ""})
        self.assertContains(r, "Le mot de passe est obligatoire.")


class AdminCreateUserAPITests(TestCase):
    url = reverse("users:api_users")

    def setUp(self):
        self.api = APIClient()
        self.admin = make_user(email=make_email("admin"), role=User.Role.ADMIN)

    def auth(self, email):
        r = self.api.post(reverse("users:token_obtain"), {"email": email, "password": PASSWORD}, format="json")
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")

    def test_admin_creates_account_via_api(self):
        self.auth(make_email("admin"))
        r = self.api.post(self.url, {"first_name": PRENOM_2, "last_name": NOM_2,
                                     "email": make_email("modifie"), "role": "UTILISATEUR"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["role"], "UTILISATEUR")
        self.assertEqual(r.data["statut"], "OUVERT")
        self.assertEqual(len(mail.outbox), 1)

    def test_api_validation(self):
        self.auth(make_email("admin"))
        r = self.api.post(self.url, {"first_name": "", "email": make_email("admin"), "role": "X"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {"first_name", "last_name", "email", "role"})

    def test_simple_user_gets_403_and_anonymous_401(self):
        self.assertEqual(self.api.get(self.url).status_code, 401)
        make_user()
        self.auth(make_email("user"))
        self.assertEqual(self.api.post(self.url, {}, format="json").status_code, 403)
