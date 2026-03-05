from django.urls import path
from .views import (
    add_journal,
    shift_info,
    list_journal,
    edit_journal,
    delete_journal,
    export_journal_pdf,
)

urlpatterns = [
    path("add-journal/", add_journal, name="add_journal"),
    path("shift-info/", shift_info, name="shift_info"),
    path("list-journal/", list_journal, name="list_journal"),
    path("edit-journal/<str:key>/", edit_journal, name="edit_journal"),
    path("delete-journal/<str:key>/", delete_journal, name="delete_journal"),
    path("export-pdf/", export_journal_pdf, name="export_journal_pdf"),
]
