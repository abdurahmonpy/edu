"""
Views for Resource Library: Admin-curated, verified guides for high school scholarship applicants.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Resource
from apps.programs.models import Program

@login_required
def resource_list_view(request):
    category_filter = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()

    resources = Resource.objects.all()
    if category_filter:
        resources = resources.filter(category=category_filter)
    if search_query:
        resources = resources.filter(title__icontains=search_query)

    return render(request, 'resources/resource_list.html', {
        'resources': resources,
        'category_filter': category_filter,
        'search_query': search_query,
        'categories': Resource.CATEGORY_CHOICES,
    })


@login_required
def resource_detail_view(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    related_resources = Resource.objects.filter(category=resource.category).exclude(id=resource.id)[:3]

    return render(request, 'resources/resource_detail.html', {
        'resource': resource,
        'related_resources': related_resources,
    })
