# from django.urls import path
# from . import views

# urlpatterns = [
#     path('', views.home, name='home'),
#     path('send/', views.send, name='send'),
#     path('dashboard/', views.dashboard, name='dashboard'),
#     path('marketplace/', views.marketplace, name='marketplace'),
# ]



from django.urls import path
from . import views

urlpatterns = [

    # ── Public ──────────────────────────────────────────────────────────────
    path('',                    views.home,                  name='home'),
    path('how-it-works/',       views.how_it_works,          name='how_it_works'),
    path('vendors/',            views.vendor_marketplace,    name='vendors'),
    path('institutions/',       views.institution_directory, name='institutions'),
    path('about/',              views.static_page,           {'page': 'about'},   name='about'),
    path('blog/',               views.static_page,           {'page': 'blog'},    name='blog'),
    path('contact/',            views.static_page,           {'page': 'contact'}, name='contact'),
    path('privacy/',            views.static_page,           {'page': 'privacy'}, name='privacy'),
    path('terms/',              views.static_page,           {'page': 'terms'},   name='terms'),
    path('security/',           views.static_page,           {'page': 'security'},name='security'),

    # ── Auth ────────────────────────────────────────────────────────────────
    path('register/',           views.register_view,         name='register'),
    path('login/',              views.login_view,            name='login'),
    path('logout/',             views.logout_view,           name='logout'),
    path('verify-email/',       views.verify_email,          name='verify_email'),

    # ── Dashboard ───────────────────────────────────────────────────────────
    path('dashboard/',          views.dashboard,             name='dashboard'),
    path('profile/',            views.profile,               name='profile'),
    path('notifications/',      views.notifications,         name='notifications'),
    path('history/',            views.transaction_history,   name='history'),

    # ── Send Money (4-step flow) ─────────────────────────────────────────────
    path('send/',               views.send_step1,            name='send_step1'),
    path('send/recipient/',     views.send_step2,            name='send_step2'),
    path('send/fees/',          views.send_step3,            name='send_step3'),
    path('send/confirm/',       views.send_confirm,          name='send_confirm'),
    path('send/receipt/<int:pk>/', views.receipt,            name='receipt'),

    # ── AJAX ────────────────────────────────────────────────────────────────
    path('api/rate/',           views.get_rate,              name='get_rate'),
]