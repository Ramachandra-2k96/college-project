from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30)
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password1', 'password2']

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    
class LoginForm_Q(forms.Form):
    image = forms.ImageField(label=" ",
        widget=forms.ClearableFileInput(attrs={'accept': 'image/png, image/jpeg', 'required': True})
    )

