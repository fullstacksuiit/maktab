from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Course URLs
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/add/', views.course_add, name='course_add'),
    path('courses/edit/<int:pk>/', views.course_edit, name='course_edit'),
    path('courses/delete/<int:pk>/', views.course_delete, name='course_delete'),
    path('courses/create-ajax/', views.course_create_ajax, name='course_create_ajax'),

    # Batch URLs
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/<int:pk>/', views.batch_detail, name='batch_detail'),
    path('batches/add/', views.batch_add, name='batch_add'),
    path('batches/edit/<int:pk>/', views.batch_edit, name='batch_edit'),
    path('batches/delete/<int:pk>/', views.batch_delete, name='batch_delete'),
    path('batches/timetable/', views.batch_timetable, name='batch_timetable'),
    path('batches/schedule-update/', views.batch_schedule_update, name='batch_schedule_update'),

    # Student URLs
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/import/', views.import_students, name='import_students'),
    path('students/import/template/', views.download_student_template, name='download_student_template'),
    path('students/<uuid:uuid>/', views.student_detail, name='student_detail'),
    path('students/edit/<uuid:uuid>/', views.student_edit, name='student_edit'),
    path('students/delete/<uuid:uuid>/', views.student_delete, name='student_delete'),
    path('students/<uuid:uuid>/fees/', views.student_fee_history, name='student_fee_history'),

    # Behavior Notes URLs
    path('students/<uuid:student_uuid>/behavior-notes/add/', views.behavior_note_add, name='behavior_note_add'),
    path('behavior-notes/edit/<int:pk>/', views.behavior_note_edit, name='behavior_note_edit'),
    path('behavior-notes/delete/<int:pk>/', views.behavior_note_delete, name='behavior_note_delete'),

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

    # Staff Leave URLs
    path('staff-leave/', views.staff_leave_list, name='staff_leave_list'),
    path('staff-leave/request/', views.staff_leave_request, name='staff_leave_request'),
    path('staff-leave/<int:pk>/', views.staff_leave_detail, name='staff_leave_detail'),
    path('staff-leave/<int:pk>/approve/', views.staff_leave_approve, name='staff_leave_approve'),
    path('staff-leave/<int:pk>/reject/', views.staff_leave_reject, name='staff_leave_reject'),
    path('staff-leave/<int:pk>/cancel/', views.staff_leave_cancel, name='staff_leave_cancel'),

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

    # Admission Application - Public URLs
    path('apply/<slug:org_slug>/', views.admission_apply, name='admission_apply'),
    path('apply/<slug:org_slug>/success/', views.admission_apply_success, name='admission_apply_success'),

    # Admission Application - Admin URLs
    path('applications/', views.application_list, name='application_list'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/accept/', views.application_accept, name='application_accept'),
    path('applications/<int:pk>/reject/', views.application_reject, name='application_reject'),

    # Parent Portal URLs
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/change-password/', views.parent_change_password, name='parent_change_password'),
    path('parent/pay/', views.parent_pay_upi, name='parent_pay_upi'),

    # Calendar & Event URLs
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/events/add/', views.event_add, name='event_add'),
    path('calendar/events/edit/<int:pk>/', views.event_edit, name='event_edit'),
    path('calendar/events/delete/<int:pk>/', views.event_delete, name='event_delete'),

    # Staff Self-Service Portal URLs
    path('my/', views.staff_portal, name='staff_portal'),
    path('my/profile/', views.staff_my_profile, name='staff_my_profile'),
    path('my/attendance/', views.staff_my_attendance, name='staff_my_attendance'),
    path('my/punch/', views.staff_punch, name='staff_punch'),
    path('my/salary/', views.staff_my_salary, name='staff_my_salary'),
    path('my/salary/<int:pk>/', views.staff_my_payslip, name='staff_my_payslip'),
    path('my/change-password/', views.staff_change_password, name='staff_change_password'),

    # Admin Payroll Management URLs
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/generate/', views.payroll_generate, name='payroll_generate'),
    path('payroll/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/<int:pk>/edit/', views.payroll_edit, name='payroll_edit'),
    path('payroll/<int:pk>/process/', views.payroll_process, name='payroll_process'),
    path('payroll/<int:pk>/mark-paid/', views.payroll_mark_paid, name='payroll_mark_paid'),
    path('payroll/<int:pk>/payslip/', views.payroll_payslip_print, name='payroll_payslip_print'),

    # Salary Components Management URLs
    path('salary-components/', views.salary_component_list, name='salary_component_list'),
    path('salary-components/add/', views.salary_component_add, name='salary_component_add'),
    path('salary-components/edit/<int:pk>/', views.salary_component_edit, name='salary_component_edit'),
    path('salary-components/delete/<int:pk>/', views.salary_component_delete, name='salary_component_delete'),

    # Accounts & Expenses URLs
    path('accounts/', views.accounts_overview, name='accounts_overview'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/edit/<int:pk>/', views.expense_edit, name='expense_edit'),
    path('expenses/delete/<int:pk>/', views.expense_delete, name='expense_delete'),

    # Export URLs
    path('export/students/', views.export_students_excel, name='export_students'),
    path('export/staff/', views.export_staff_excel, name='export_staff'),
    path('export/attendance/', views.export_attendance_excel, name='export_attendance'),
    path('export/payments/', views.export_fee_payments_excel, name='export_fee_payments'),
]
