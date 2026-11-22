from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.testing import make_user

from .models import Document


User = get_user_model()


class DocumentPermissionTests(TestCase):
    def setUp(self):
        self.document = Document.objects.create(
            titreDocument="Document test",
            descDocument="Description test",
        )
        self.detail_url = reverse("DocumentApp:detail", args=[self.document.pk])
        self.create_url = reverse("DocumentApp:ajouter")
        self.update_url = reverse("DocumentApp:modifier", args=[self.document.pk])
        self.delete_url = reverse("DocumentApp:supprimer", args=[self.document.pk])
        self.list_url = reverse("DocumentApp:liste")
        self.simple_user = make_user()
        self.admin = make_user(role=User.Role.ADMIN)

    def test_anonymous_is_redirected_to_login(self):
        urls = (self.detail_url, self.create_url, self.update_url)
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('users:login')}?next={url}")

        response = self.client.post(self.delete_url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.delete_url}")

    def test_simple_user_is_refused_admin_views(self):
        self.client.force_login(self.simple_user)

        for url in (self.detail_url, self.create_url, self.update_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, self.list_url)

        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertTrue(Document.objects.filter(pk=self.document.pk).exists())

    def test_admin_can_create_detail_update_and_delete_document(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            self.create_url,
            {"titreDocument": "Nouveau document", "descDocument": "Nouvelle description"},
        )
        created = Document.objects.get(titreDocument="Nouveau document")
        self.assertRedirects(
            response,
            reverse("DocumentApp:detail", args=[created.pk]),
        )
        self.assertEqual(
            self.client.get(reverse("DocumentApp:detail", args=[created.pk])).status_code,
            200,
        )

        response = self.client.post(
            reverse("DocumentApp:modifier", args=[created.pk]),
            {"titreDocument": "Document modifié", "descDocument": "Description modifiée"},
        )
        created.refresh_from_db()
        self.assertEqual(created.titreDocument, "Document modifié")
        self.assertRedirects(
            response,
            reverse("DocumentApp:detail", args=[created.pk]),
        )

        response = self.client.post(
            reverse("DocumentApp:supprimer", args=[created.pk]),
        )
        self.assertRedirects(response, self.list_url)
        self.assertFalse(Document.objects.filter(pk=created.pk).exists())

    def test_simple_user_can_open_document_list(self):
        self.client.force_login(self.simple_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Document test")
