from django import forms

from .models import PaymentReceipt


class CheckoutForm(forms.Form):
    receiver_name = forms.CharField(
        label="نام گیرنده",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm"}),
    )
    receiver_phone = forms.CharField(
        label="موبایل گیرنده",
        max_length=11,
        widget=forms.TextInput(
            attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm", "dir": "ltr"}
        ),
    )
    province = forms.CharField(
        label="استان",
        max_length=80,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm"}),
    )
    city = forms.CharField(
        label="شهر",
        max_length=80,
        widget=forms.TextInput(attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm"}),
    )
    postal_code = forms.CharField(
        label="کد پستی",
        max_length=10,
        widget=forms.TextInput(
            attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm", "dir": "ltr"}
        ),
    )
    address = forms.CharField(
        label="آدرس کامل",
        widget=forms.Textarea(
            attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm", "rows": 3}
        ),
    )
    user_note = forms.CharField(
        label="توضیحات سفارش (اختیاری)",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "w-full rounded-xl border px-4 py-2.5 text-sm", "rows": 2}
        ),
    )


class ReceiptUploadForm(forms.ModelForm):
    class Meta:
        model = PaymentReceipt
        fields = ("image", "tracking_code", "amount")
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={"class": "w-full text-sm", "accept": "image/*,.pdf"}
            ),
            "tracking_code": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border px-4 py-2.5 text-sm",
                    "placeholder": "کد پیگیری در صورت وجود",
                    "dir": "ltr",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border px-4 py-2.5 text-sm",
                    "placeholder": "مبلغ واریزی (تومان)",
                    "dir": "ltr",
                }
            ),
        }
        labels = {
            "image": "تصویر فیش واریز",
            "tracking_code": "کد پیگیری",
            "amount": "مبلغ واریزی",
        }
