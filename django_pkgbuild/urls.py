from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^login/$', views.login_view, name='login'),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^add_repository/$', views.add_repository, name='add_repository'),
    url(r'^modify_repository/$', views.modify_repository, name='modify_repository'),
    url(r'^build/$', views.build, name='build'),
    url(r'^build_all/$', views.build_all, name='build_all'),
    url(r'^add/$', views.add, name='add'),
    url(r'^remove/$', views.remove, name='remove'),
]
