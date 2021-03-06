import os
from django.contrib.auth import authenticate, login, logout
from django.http.response import HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.shortcuts import render
from trans.forms import UploadFileForm

from trans.models import User, Translation
from trans.utils.pdf import unreleased_pdf_path


class FirstPage(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect(to=reverse('admin:index'))
        if request.user.groups.filter(name="staff").exists():
            return redirect(to=reverse('users_list'))

        if request.user.is_authenticated():
            return redirect(to=reverse('home'))
        else:
            return render(request, 'login.html')

class Login(View):
    def post(self, request):
        username = request.POST.get('mail')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        # @milad you should probably verify this, it's supposed to login the user
        user = authenticate(username=username, password=password)

        if user is not None:
            if remember_me is None:
                self.request.session.set_expiry(0)
            else:
                self.request.session.set_expiry(1209600)

            login(request, user)

            return redirect(to=reverse('firstpage'))

        return render(request, 'login.html', {'login_error': True})


class Settings(LoginRequiredMixin,View):
    def get(self, request):
        user = User.objects.get(username=request.user)
        form = UploadFileForm()
        return render(request, 'settings.html', {'form': form, 'text_font_name': user.text_font_name})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if not form.is_valid():
            return HttpResponseBadRequest("You should attach a file")
        font_file = request.FILES['uploaded_file']
        if not font_file:
            return HttpResponseBadRequest("You should attach a file")
        import base64
        text_font_base64 = base64.b64encode(font_file.read())
        user = User.objects.get(username=request.user.username)
        for trans in Translation.objects.filter(user=user):
            if os.path.exists(unreleased_pdf_path(trans.task.contest.slug, trans.task.name, user)):
                os.remove(unreleased_pdf_path(trans.task.contest.slug, trans.task.name, user))
        user.text_font_base64 = text_font_base64
        user.text_font_name = font_file.name
        user.save()
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    def delete(self, request):
        user = User.objects.get(username=request.user)
        for trans in Translation.objects.filter(user=user):
            if os.path.exists(unreleased_pdf_path(trans.task.contest.slug, trans.task.name, user)):
                os.remove(unreleased_pdf_path(trans.task.contest.slug, trans.task.name, user))

        user.text_font_base64 = ''
        user.text_font_name = ''
        user.save()
        return JsonResponse({'message': "Done"})


class Logout(LoginRequiredMixin,View):
    def get(self, request):
        logout(request)
        return redirect(request=request, to=reverse('firstpage'))
