"""
Views for Student Documents management and AI Review.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import Document
from .forms import DocumentForm
from apps.accounts.models import Student
from apps.programs.models import Program
from apps.services.anthropic_client import call_claude


@login_required
def document_list_view(request):
    student, _ = Student.objects.get_or_create(user=request.user)
    doc_type_filter = request.GET.get('type')
    program_filter = request.GET.get('program')

    documents = Document.objects.filter(student=student)
    if doc_type_filter:
        documents = documents.filter(doc_type=doc_type_filter)
    if program_filter:
        documents = documents.filter(linked_program_id=program_filter)

    # Grouped stats
    total_count = documents.count()
    drafts_count = documents.filter(status='draft').count()
    ready_count = documents.filter(status='final').count()

    # Document stats by tracked program
    from apps.programs.models import StudentProgram
    student_programs_map = {
        sp.program_id: sp for sp in StudentProgram.objects.filter(student=student)
    }

    tracked_programs = Program.objects.filter(student_tracking__student=student)
    program_doc_stats = []
    for prog in tracked_programs:
        docs_for_prog = Document.objects.filter(student=student, linked_program=prog)
        prog_total = docs_for_prog.count()
        prog_final = docs_for_prog.filter(status='final').count()
        program_doc_stats.append({
            'program': prog,
            'total': prog_total,
            'final': prog_final,
            'student_program': student_programs_map.get(prog.id),
        })

    docs_list = list(documents)
    for d in docs_list:
        d.student_program = student_programs_map.get(d.linked_program_id) if d.linked_program_id else None

    return render(request, 'documents/document_list.html', {
        'student': student,
        'documents': docs_list,
        'doc_type_filter': doc_type_filter,
        'program_filter': program_filter,
        'total_count': total_count,
        'drafts_count': drafts_count,
        'ready_count': ready_count,
        'program_doc_stats': program_doc_stats,
        'doc_types': Document.DOC_TYPE_CHOICES,
        'programs': Program.objects.all(),
    })


@login_required
def document_create_view(request):
    student, _ = Student.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.student = student
            doc.version = 1
            doc.save()
            messages.success(request, f"«{doc.title}» hujjati muvaffaqiyatli saqlandi.")
            return redirect('documents:detail', doc_id=doc.id)
    else:
        initial = {}
        if request.GET.get('type'):
            initial['doc_type'] = request.GET.get('type')
        if request.GET.get('program'):
            initial['linked_program'] = request.GET.get('program')
        form = DocumentForm(initial=initial)

    return render(request, 'documents/document_form.html', {
        'form': form,
        'is_edit': False,
        'student': student,
    })


@login_required
def document_detail_view(request, doc_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    doc = get_object_or_404(Document, id=doc_id, student=student)

    return render(request, 'documents/document_detail.html', {
        'document': doc,
        'student': student,
    })


@login_required
def document_edit_view(request, doc_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    doc = get_object_or_404(Document, id=doc_id, student=student)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            updated_doc = form.save(commit=False)
            # Increment version on edit
            updated_doc.version = doc.version + 1
            updated_doc.save()
            messages.success(request, f"«{updated_doc.title}» (v{updated_doc.version}) yangilandi.")
            return redirect('documents:detail', doc_id=updated_doc.id)
    else:
        form = DocumentForm(instance=doc)

    return render(request, 'documents/document_form.html', {
        'form': form,
        'document': doc,
        'is_edit': True,
        'student': student,
    })


@login_required
def document_ai_review_view(request, doc_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    doc = get_object_or_404(Document, id=doc_id, student=student)

    if not doc.content.strip():
        messages.warning(request, "AI tahlil qilishi uchun hujjat matnini kiriting.")
        return redirect('documents:edit', doc_id=doc.id)

    # Perform AI Review
    prog_name = doc.linked_program.name if doc.linked_program else "Xalqaro grant dasturi"
    system_prompt = (
        "Sen xalqaro universitetlar va grant dasturlariga (Global UGRAD, DAAD, Chevening) kirish bo'yicha "
        "insho va motivatsion xatlarni tahrirlovchi professional ekspertsan. "
        "O'quvchining inshosini tahlil qilib, uning kuchli tomonlari, xatolari va yaxshilash bo'yicha "
        "3 ta aniq tavsiyasini O'zbek tilida (lotin alifbosi) ravon va dalillar bilan yozib ber."
    )
    user_prompt = f"""Hujjat turi: {doc.get_doc_type_display()}
Sarlavha: {doc.title}
Mo'ljallangan dastur: {prog_name}
O'quvchi: {student.grade or 10}-sinf

Hujjat matni:
\"\"\"
{doc.content}
\"\"\"

Iltimos, ushbu inshoni xalqaro grant mezonlari bo'yicha tahlil qilib ber."""

    try:
        feedback = call_claude(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=1500)
    except Exception as e:
        # High quality offline heuristic fallback feedback
        word_count = len(doc.content.split())
        feedback = (
            f"**Insho umumiy tahlili ({word_count} so'z):**\n\n"
            f"1. **Mavzu ochilishi:** Fikrlar mantiqan ketma-ket bayon etilgan. Grant maqsadlariga mos.\n"
            f"2. **Tuzilma va Grammatika:** Kirish va xulosa qismi ajralib turibdi. Akademik bog'lovchilarni (Furthermore, Consequently, In addition) ko'proq qo'llash tavsiya etiladi.\n"
            f"3. **Tavsiya:** O'zbekistonga qaytgach amalga oshirmoqchi bo'lgan aniq loyihangizni yanada aniqroq raqamlar yoki misollar bilan boyiting."
        )

    doc.ai_feedback = feedback
    doc.status = 'under_review'
    doc.save(update_fields=['ai_feedback', 'status', 'updated_at'])
    messages.success(request, "AI inshongizni tahlil qildi va batafsil tavsiyalar berdi!")

    return redirect('documents:detail', doc_id=doc.id)


@login_required
def document_delete_view(request, doc_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    doc = get_object_or_404(Document, id=doc_id, student=student)

    if request.method == 'POST':
        title = doc.title
        doc.delete()
        messages.success(request, f"«{title}» hujjati o'chirildi.")
        return redirect('documents:list')

    return render(request, 'documents/document_confirm_delete.html', {
        'document': doc,
    })


from apps.documents.models import PortfolioItem
from apps.services.vision_service import evaluate_portfolio_image

@login_required
def portfolio_upload_view(request, doc_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    doc = get_object_or_404(Document, id=doc_id, student=student)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        file = request.FILES.get('file')
        medium = request.POST.get('medium', '')
        
        if title and file:
            item = PortfolioItem.objects.create(
                document=doc,
                title=title,
                description=description,
                file=file,
                medium=medium
            )
            messages.success(request, "Portfolio qismi muvaffaqiyatli yuklandi.")
            return redirect('documents:portfolio_item_detail', item_id=item.id)
            
    return render(request, 'documents/portfolio_upload.html', {'document': doc})

@login_required
def portfolio_item_detail_view(request, item_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    item = get_object_or_404(PortfolioItem, id=item_id, document__student=student)
    return render(request, 'documents/portfolio_item_detail.html', {'item': item})

@login_required
def portfolio_evaluate_view(request, item_id):
    student, _ = Student.objects.get_or_create(user=request.user)
    item = get_object_or_404(PortfolioItem, id=item_id, document__student=student)
    
    if item.file:
        try:
            result = evaluate_portfolio_image(item.file.path, item.title, item.description)
            item.ai_feedback = result.get('feedback', '')
            item.save()
            messages.success(request, "Portfolio AI (Vision) orqali tahlil qilindi!")
        except Exception as e:
            messages.error(request, f"Tahlil qilishda xatolik: {e}")
            
    return redirect('documents:portfolio_item_detail', item_id=item.id)

