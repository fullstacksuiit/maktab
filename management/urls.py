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
    path('courses/create-ajax/', views.course_create_ajax, name='course_create_ajax'),

    # Batch URLs
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/add/', views.batch_add, name='batch_add'),
    path('batches/edit/<int:pk>/', views.batch_edit, name='batch_edit'),
    path('batches/delete/<int:pk>/', views.batch_delete, name='batch_delete'),

    # Student URLs
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/import/', views.import_students, name='import_students'),
    path('students/import/template/', views.download_student_template, name='download_student_template'),
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
    path('attendance/quick/<int:batch_id>/', views.quick_attendance, name='quick_attendance'),
    path('attendance/toggle/', views.toggle_attendance, name='toggle_attendance'),
    path('attendance/mark-all-present/', views.mark_all_present, name='mark_all_present'),
    path('attendance/mark-all-absent/', views.mark_all_absent, name='mark_all_absent'),

    # Staff Attendance URLs
    path('staff-attendance/', views.staff_attendance_list, name='staff_attendance_list'),
    path('staff-attendance/mark/', views.staff_attendance_mark, name='staff_attendance_mark'),
    path('staff-attendance/quick/', views.staff_quick_attendance, name='staff_quick_attendance'),
    path('staff-attendance/toggle/', views.staff_toggle_attendance, name='staff_toggle_attendance'),
    path('staff-attendance/mark-all-present/', views.staff_mark_all_present, name='staff_mark_all_present'),
    path('staff-attendance/mark-all-absent/', views.staff_mark_all_absent, name='staff_mark_all_absent'),

    # Fee Payment URLs
    path('payments/', views.fee_payment_list, name='fee_payment_list'),
    path('payments/add/', views.fee_payment_add, name='fee_payment_add'),
    path('payments/edit/<int:pk>/', views.fee_payment_edit, name='fee_payment_edit'),
    path('payments/delete/<int:pk>/', views.fee_payment_delete, name='fee_payment_delete'),
    path('payments/print/<int:pk>/', views.print_receipt, name='print_receipt'),

    # User Management URLs
    path('users/', views.user_list, name='user_list'),
    path('users/invite/', views.user_invite, name='user_invite'),
    path('users/edit/<int:pk>/', views.user_edit, name='user_edit'),
    path('users/delete/<int:pk>/', views.user_delete, name='user_delete'),

    # Settings
    path('settings/', views.settings_view, name='settings'),

    # API
    path('api/cities/', views.get_cities_for_state, name='api_cities'),

    # Parent Portal URLs
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/change-password/', views.parent_change_password, name='parent_change_password'),

    # Export URLs
    path('export/students/', views.export_students_excel, name='export_students'),
    path('export/staff/', views.export_staff_excel, name='export_staff'),
    path('export/attendance/', views.export_attendance_excel, name='export_attendance'),
    path('export/payments/', views.export_fee_payments_excel, name='export_fee_payments'),
]
