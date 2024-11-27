# urls.py
from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/edit/', EditProfileView.as_view(), name='edit-profile'),
    path('edit-avatar/', EditAvatarView.as_view(), name='edit-avatar'),
    path('tasks/create/me/', CreateTaskForMeView.as_view(), name='create_task_me'),
    path('tasks/pending/', UserPendingTasksView.as_view(), name='user_pending_task'),
    path('tasks/<int:task_id>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:task_id>/change-status/', ChangeTaskStatusView.as_view(), name='change-task-status'),
    path('tasks/date/<str:specific_date>/', UserSpecificDateTasksView.as_view(), name='tasks-specific-date'),
    path('tasks/date-range/<str:start_date>/<str:end_date>/', UserSpecificDateRangeTasksView.as_view(), name='tasks-date-range'),
    path('projects/', ProjectListView.as_view(), name='project-list'),
    path('projects/<int:project_id>/', ProjectDetailView.as_view(), name='project-detail'),
    path('create-ticket/', CreateTicketTaskView.as_view(), name='create_ticket_task'),
    path('projects/<int:project_id>/tickets/', ProjectTicketsView.as_view(), name='project-tickets'),
    path('tickets/<int:task_id>/change-status/', ChangeTicketStatusView.as_view(), name='change-task-status'),
    path('projects/<int:project_id>/add-member/', AddMemberToProjectView.as_view(), name='add-member-to-project'),
    path('users/', UserListView.as_view(), name='user-list'),  # Endpoint to get all users
    path('projects/latest-high-priority/', LatestHighPriorityProjectsView.as_view(), name='latest-high-priority-projects'),
    path('notifications/', GetUserNotificationsView.as_view(), name='get_notifications'),
    path('notifications/mark-as-read/', MarkNotificationAsReadView.as_view(), name='mark_notifications_as_read'),
    path('notifications/unread/', UnreadNotificationAPIView.as_view(), name='unread_notifications'),
]
