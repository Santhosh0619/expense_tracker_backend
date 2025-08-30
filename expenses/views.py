import json, calendar, io
from datetime import date
from decimal import Decimal
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from openpyxl import Workbook

from .models import Expense, Budget, Category

def _require_auth(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error':'Auth required'}, status=401)
    return None

def _month_range(year, month):
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)

# ---------- Module 2: Dashboard ----------
def dashboard(request, year, month):
    err = _require_auth(request)
    if err: return err
    start, end = _month_range(year, month)
    qs = Expense.objects.filter(user=request.user, date__range=(start, end))
    total = qs.aggregate(s=Sum('amount'))['s'] or 0
    daywise = {}
    for e in qs.order_by('-date','-id'):
        daywise.setdefault(str(e.date), []).append({
            'id': e.id, 'category': e.category.name, 'amount': float(e.amount), 'notes': e.notes
        })
    budget = Budget.objects.filter(user=request.user, year=year, month=month).first()
    response = {
        'total_spend': float(total),
        'budget': float(budget.monthly_budget) if budget else None,
        'salary': float(budget.monthly_salary) if budget else None,
        'daily': daywise,
    }
    return JsonResponse(response)

# ---------- Module 3: Expense Entry ----------
@csrf_exempt
def expenses_crud(request):
    err = _require_auth(request)
    if err: return err

    if request.method == 'GET':
        year = int(request.GET.get('year'))
        month = int(request.GET.get('month'))
        start, end = _month_range(year, month)
        qs = Expense.objects.filter(user=request.user, date__range=(start, end)).select_related('category')
        return JsonResponse([{
            'id': e.id,'date': str(e.date),'category': e.category.name,'category_id': e.category_id,
            'amount': float(e.amount),'notes': e.notes
        } for e in qs.order_by('-date','-id')], safe=False)

    if request.method == 'POST':
        data = json.loads(request.body.decode())
        cat_name = data.get('category')
        category = None
        if 'category_id' in data and data['category_id']:
            category = Category.objects.get(id=data['category_id'])
        else:
            category, _ = Category.objects.get_or_create(name=cat_name)
        e = Expense.objects.create(
            user=request.user,
            date=data.get('date'),
            category=category,
            amount=Decimal(str(data.get('amount'))),
            notes=data.get('notes','')
        )
        return JsonResponse({'id': e.id})

    if request.method == 'PUT':
        data = json.loads(request.body.decode())
        e = Expense.objects.get(id=data['id'], user=request.user)
        if 'category_id' in data:
            e.category_id = data['category_id']
        elif 'category' in data:
            e.category, _ = Category.objects.get_or_create(name=data['category'])
        if 'date' in data: e.date = data['date']
        if 'amount' in data: e.amount = Decimal(str(data['amount']))
        if 'notes' in data: e.notes = data['notes']
        e.save()
        return JsonResponse({'message':'updated'})

    if request.method == 'DELETE':
        data = json.loads(request.body.decode())
        Expense.objects.filter(id=data['id'], user=request.user).delete()
        return JsonResponse({'message':'deleted'})

    return JsonResponse({'error':'Unsupported method'}, status=405)

# ---------- Module 4: Budget Management ----------
@csrf_exempt
def budget_crud(request, year, month):
    err = _require_auth(request)
    if err: return err

    if request.method == 'GET':
        b = Budget.objects.filter(user=request.user, year=year, month=month).first()
        if not b:
            return JsonResponse({'year':year,'month':month,'monthly_salary':None,'monthly_budget':None})
        return JsonResponse({
            'year':year,'month':month,
            'monthly_salary': float(b.monthly_salary),
            'monthly_budget': float(b.monthly_budget)
        })

    if request.method == 'POST':
        data = json.loads(request.body.decode())
        b, _ = Budget.objects.update_or_create(
            user=request.user, year=year, month=month,
            defaults={
                'monthly_salary': Decimal(str(data.get('monthly_salary'))),
                'monthly_budget': Decimal(str(data.get('monthly_budget')))
            }
        )
        return JsonResponse({'message':'saved'})
    return JsonResponse({'error':'Unsupported method'}, status=405)

# ---------- Module 5: Category-wise Analysis ----------
def category_analysis(request, year, month):
    err = _require_auth(request)
    if err: return err
    start, end = _month_range(year, month)
    qs = Expense.objects.filter(user=request.user, date__range=(start, end))
    grouped = (qs.values('category__name')
                 .annotate(total=Sum('amount'))
                 .order_by('-total'))
    b = Budget.objects.filter(user=request.user, year=year, month=month).first()
    salary = b.monthly_salary if b else Decimal('0')

    # heuristics for suggestions: if category > 20% salary, flag
    suggestions = []
    for g in grouped:
        percent = (Decimal(g['total'])/salary*100) if salary else Decimal('0')
        if salary and percent >= 20:
            suggestions.append({
                'category': g['category__name'],
                'message': f"High spend in {g['category__name']} ({percent:.1f}% of salary). Consider cutting down."
            })

    total_spend = qs.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    overall_msg = None
    if b and total_spend > b.monthly_salary:
        overall_msg = "Warning: Total expenses exceed your monthly salary."
    elif b and total_spend > b.monthly_budget:
        overall_msg = "Caution: You crossed your monthly budget."

    return JsonResponse({
        'by_category': [{'category':g['category__name'],'total':float(g['total'])} for g in grouped],
        'total_spend': float(total_spend),
        'salary': float(salary) if b else None,
        'suggestions': suggestions,
        'overall_message': overall_msg
    })

# ---------- Module 6: History & Reports ----------
def history(request):
    err = _require_auth(request)
    if err: return err
    # optional filters: ?category=Food&year=2025
    qs = Expense.objects.filter(user=request.user)
    if 'category' in request.GET:
        qs = qs.filter(category__name=request.GET['category'])
    if 'year' in request.GET:
        qs = qs.filter(date__year=int(request.GET['year']))
    if 'month' in request.GET:
        qs = qs.filter(date__month=int(request.GET['month']))
    agg = (qs.values('date__year','date__month')
             .annotate(total=Sum('amount'))
             .order_by('-date__year','-date__month'))
     # ✅ Fix: iterate over results
    results = [
        {
            'year': row['date__year'],
            'month': row['date__month'],
            'total': float(row['total'])
        }
        for row in agg
    ]
    return JsonResponse(results, safe=False)

# ---------- Excel export ----------
def export_excel(request, year, month):
    err = _require_auth(request)
    if err: return err
    start, end = _month_range(year, month)
    qs = Expense.objects.filter(user=request.user, date__range=(start, end)).select_related('category')
    b = Budget.objects.filter(user=request.user, year=year, month=month).first()

    wb = Workbook()
    ws = wb.active
    ws.title = f"{year}-{month:02d}"

    ws.append(["Date","Category","Amount","Notes"])
    for e in qs.order_by('date','id'):
        ws.append([str(e.date), e.category.name, float(e.amount), e.notes])

    ws2 = wb.create_sheet("Summary")
    total = qs.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    ws2.append(["Total Spend", float(total)])
    if b:
        ws2.append(["Salary", float(b.monthly_salary)])
        ws2.append(["Budget", float(b.monthly_budget)])
        ws2.append(["Over Salary?", "YES" if total > b.monthly_salary else "NO"])
        ws2.append(["Over Budget?", "YES" if total > b.monthly_budget else "NO"])

    # category breakdown
    ws2.append([])
    ws2.append(["Category","Total"])
    for row in (qs.values('category__name').annotate(total=Sum('amount')).order_by('-total')):
        ws2.append([row['category__name'], float(row['total'])])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = f"expenses_{year}_{month:02d}.xlsx"
    return FileResponse(bio, as_attachment=True, filename=filename)
