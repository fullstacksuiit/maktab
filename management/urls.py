from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Course URLs
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.course_add, name='course_add'),
    path('courses/edit/<int:pk>/', views.course_edit, name='course_edit'),
    path('courses/delete/<int:pk>/', views.course_delete, name='course_delete'),

    # Student URLs
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/edit/<int:pk>/', views.student_edit, name='student_edit'),
    path('students/delete/<int:pk>/', views.student_delete, name='student_delete'),
    path('students/<int:pk>/fees/', views.student_fee_history, name='student_fee_history'),

    # Staff URLs
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_add, name='staff_add'),
    path('staff/<int:pk>/', views.staff_detail, name='staff_detail'),
    path('staff/edit/<int:pk>/', views.staff_edit, name='staff_edit'),
    path('staff/delete/<int:pk>/', views.staff_delete, name='staff_delete'),

    # Attendance URLs
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/mark/', views.attendance_mark, name='attendance_mark'),

    # Fee Payment URLs
    path('payments/', views.fee_payment_list, name='fee_payment_list'),
    path('payments/add/', views.fee_payment_add, name='fee_payment_add'),

    # Settings
    path('settings/', views.settings_view, name='settings'),

    # Export URLs
    path('export/students/', views.export_students_excel, name='export_students'),
    path('export/staff/', views.export_staff_excel, name='export_staff'),
    path('export/attendance/', views.export_attendance_excel, name='export_attendance'),
]
