from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()
PASSWORD = "MotDePasse-Test-123"


def make_user(email="user@dochub.test", role=User.Role.UTILISATEUR, **kw):
    return User.objects.create_user(
        email=email, password=PASSWORD, first_name="Test", last_name="User", role=role, **kw
    )


class UserModelTests(TestCase):
    def test_email_is_normalized_and_role_defaults_to_user(self):
        u = make_user(email="Someone@DocHub.TEST")
        self.assertEqual(u.email, "someone@dochub.test")
        self.assertEqual(u.role, User.Role.UTILISATEUR)
        self.assertFalse(u.is_admin)
        self.assertFalse(u.is_staff)

    def test_admin_role_gives_staff_access(self):
        u = make_user(role=User.Role.ADMIN)
        self.assertTrue(u.is_admin)
        self.assertTrue(u.is_staff)

    def test_superuser_is_admin(self):
        u = User.objects.create_superuser("root@dochub.test", PASSWORD, first_name="R", last_name="R")
        self.assertTrue(u.is_admin)


class LoginPageTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def post_login(self, email, password):
        return self.client.post(reverse("users:login"), {"username": email, "password": password})

    def test_login_success_redirects_to_dashboard(self):
        r = self.post_login("user@dochub.test", PASSWORD)
        self.assertRedirects(r, reverse("users:dashboard"))

    def test_login_is_case_insensitive_on_email(self):
        r = self.post_login("USER@dochub.test", PASSWORD)
        self.assertRedirects(r, reverse("users:dashboard"))

    def test_wrong_password_shows_error(self):
        r = self.post_login("user@dochub.test", "mauvais")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Email ou mot de passe incorrect")

    def test_invalid_email_and_empty_fields_are_rejected(self):
        r = self.post_login("pas-un-email", PASSWORD)
        self.assertContains(r, "Saisissez une adresse email valide.")
        r = self.post_login("", "")
        self.assertContains(r, "L&#x27;adresse email est obligatoire.")
        self.assertContains(r, "Le mot de passe est obligatoire.")

    def test_deactivated_account_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        r = self.post_login("user@dochub.test", PASSWORD)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_page_uses_mockup_template(self):
        r = self.client.get(reverse("users:login"))
        self.assertTemplateUsed(r, "users/login.html")
        self.assertContains(r, "Se souvenir de moi")
        self.assertContains(r, "css/dochub.css")

    def test_session_persists_across_requests(self):
        self.post_login("user@dochub.test", PASSWORD)
        self.assertEqual(self.client.get(reverse("users:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("users:dashboard")).status_code, 200)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_without_remember_me_session_ends_with_browser(self):
        self.post_login("user@dochub.test", PASSWORD)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_with_remember_me_session_is_kept(self):
        self.client.post(reverse("users:login"),
                         {"username": "user@dochub.test", "password": PASSWORD, "remember_me": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_logout(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("users:logout"))
        self.assertRedirects(r, reverse("users:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class PagePermissionTests(TestCase):
    def test_anonymous_is_redirected_to_login(self):
        r = self.client.get(reverse("users:dashboard"))
        self.assertRedirects(r, reverse("users:login") + "?next=/")

    def test_user_cannot_access_admin_space(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("users:admin_space")).status_code, 403)

    def test_logged_in_pages_are_never_cached(self):
        self.client.force_login(make_user(role=User.Role.ADMIN))
        for name in ["users:dashboard", "users:admin_space"]:
            cc = self.client.get(reverse(name))["Cache-Control"]
            self.assertIn("no-store", cc)
            self.assertIn("private", cc)

    def test_back_button_after_switching_account_shows_no_admin_page(self):
        # Admin connecté -> déconnexion -> connexion en tant qu'utilisateur
        self.client.force_login(make_user(email="a@dochub.test", role=User.Role.ADMIN))
        self.client.post(reverse("users:logout"))
        self.client.force_login(make_user())
        # Le navigateur redemande la page (no-store) : la session actuelle s'applique
        self.assertEqual(self.client.get(reverse("users:admin_space")).status_code, 403)

    def test_admin_can_access_admin_space(self):
        self.client.force_login(make_user(role=User.Role.ADMIN))
        self.assertEqual(self.client.get(reverse("users:admin_space")).status_code, 200)


class JWTTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = make_user()

    def test_obtain_token_and_access_protected_route(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": "user@dochub.test", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)

        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        me = self.api.get(reverse("users:me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], "user@dochub.test")
        self.assertEqual(me.data["role"], "UTILISATEUR")

    def test_protected_route_without_token_is_refused(self):
        self.assertEqual(self.api.get(reverse("users:me")).status_code, 401)

    def test_wrong_credentials_give_401(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": "user@dochub.test", "password": "mauvais"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_deactivated_account_gets_no_token(self):
        self.user.is_active = False
        self.user.save()
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": "user@dochub.test", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_refresh_token(self):
        r = self.api.post(reverse("users:token_obtain"),
                          {"email": "user@dochub.test", "password": PASSWORD}, format="json")
        r2 = self.api.post(reverse("users:token_refresh"), {"refresh": r.data["refresh"]}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access", r2.data)
