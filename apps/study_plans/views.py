"""
Views for study plans.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def plan_detail_view(request):
    """
    Study plan detail view placeholder.
    """
    return render(request, 'base.html')
