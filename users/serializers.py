from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .forms import clean_new_email, clean_person_name

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "statut", "is_active", "date_joined", "last_login"]
        read_only_fields = fields


class AdminCreateUserSerializer(serializers.Serializer):
    """US-05 via l'API : mêmes contrôles de saisie que le formulaire de la page."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.UTILISATEUR)
    statut = serializers.ChoiceField(choices=User.Statut.choices, default=User.Statut.OUVERT)

    @staticmethod
    def _run(check, value):
        try:
            return check(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)

    def validate_first_name(self, v):
        return self._run(clean_person_name, v)

    def validate_last_name(self, v):
        return self._run(clean_person_name, v)

    def validate_email(self, v):
        return self._run(clean_new_email, v)
