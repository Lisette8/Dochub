from django.db import models

# Create your models here.
class Document(models.Model):
  idDocument = models.BigAutoField(primary_key=True)
  titreDocument = models.CharField(max_length=50)
  descDocument = models.TextField(max_length=200)
  created_at = models.DateField(auto_now_add=True, auto_now=True)
  updated_at = models.DateField(auto_now=True)
  