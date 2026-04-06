from django import forms

class SearchForm(forms.Form):
    case_number = forms.CharField(required=False)