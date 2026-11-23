"""
Management command : fix_documents_type
Corrige le type_document et la thematique des documents existants dont
les colonnes sont NULL ou 'AUTRE', en se basant sur l'extension du fichier.

Usage :
    python manage.py fix_documents_type
"""
import os
from django.core.management.base import BaseCommand
from DocumentApp.models import Document


class Command(BaseCommand):
    help = "Corrige type_document des documents existants depuis leur extension de fichier."

    def handle(self, *args, **options):
        ext_map = {
            ".pdf": Document.TypeDocument.PDF,
            ".md": Document.TypeDocument.MARKDOWN,
            ".markdown": Document.TypeDocument.MARKDOWN,
            ".txt": Document.TypeDocument.TEXTE,
        }

        docs = Document.objects.all()
        fixed = 0
        for doc in docs:
            changed = False
            # Fix type_document
            try:
                if doc.fichier and doc.fichier.name:
                    _, ext = os.path.splitext(doc.fichier.name.lower())
                    new_type = ext_map.get(ext)
                    if new_type and (not doc.type_document or doc.type_document == Document.TypeDocument.AUTRE):
                        doc.type_document = new_type
                        changed = True
            except Exception:
                pass

            # Fix thematique : si NULL ou vide, mettre AUTRE (valeur neutre correcte)
            try:
                if not doc.thematique:
                    doc.thematique = Document.Thematique.AUTRE
                    changed = True
            except Exception:
                pass

            if changed:
                try:
                    Document.objects.filter(pk=doc.pk).update(
                        type_document=doc.type_document,
                        thematique=doc.thematique,
                    )
                    fixed += 1
                    self.stdout.write(f"  → Corrigé : {doc.titreDocument} (type={doc.type_document}, thematique={doc.thematique})")
                except Exception as e:
                    self.stderr.write(f"  ✗ Erreur sur {doc.titreDocument} : {e}")

        self.stdout.write(self.style.SUCCESS(f"\n✓ {fixed} document(s) corrigé(s)."))
