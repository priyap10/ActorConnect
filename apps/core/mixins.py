from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request, default):
    
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


class OwnedQuerysetMixin:
   

    owner_field = "owner"

    def get_queryset(self):
        return super().get_queryset().filter(**{self.owner_field: self.request.user})


class SuccessMessageMixin:
    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response