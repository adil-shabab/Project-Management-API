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

]
