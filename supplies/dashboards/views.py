import json
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.timezone import now, localtime 
from datetime import timedelta, datetime
from django.db.models import Count, Sum
from django.utils.dateformat import format as date_format
from supplies.models import SupplyItem, SupplyBatch, SupplyCategory
from django.utils import timezone

timezone.activate("America/Sao_Paulo")

def calc_variation(today_value, yesterday_value):
    if yesterday_value == 0:
        return ("—", True) if today_value == 0 else ("+∞%", True)
    diff = today_value - yesterday_value
    percent = (diff / yesterday_value) * 100
    symbol = "↑" if percent >= 0 else "↓"
    return (f"{symbol} {abs(percent):.0f}% desde ontem", percent >= 0)

@staff_member_required
def supplies_dashboard(request):
    timezone.activate("America/Sao_Paulo")
    today = localtime().date()  # ← Corrigido aqui
    yesterday = today - timedelta(days=1)
    next_7_days = today + timedelta(days=7)

    # Hoje
    total_items = SupplyItem.objects.count()
    total_active = SupplyItem.objects.filter(is_active=True).count()
    total_expired = SupplyBatch.objects.filter(expiration_date__lt=today).count()
    expiring_soon = SupplyBatch.objects.filter(expiration_date__range=(today, next_7_days)).count()
    total_valid = SupplyBatch.objects.filter(expiration_date__gte=next_7_days).count()

    # Ontem (para comparação)
    total_items_yesterday = SupplyItem.objects.filter(created_at__lt=today).count()
    total_active_yesterday = SupplyItem.objects.filter(is_active=True, created_at__lt=today).count()
    total_expired_yesterday = SupplyBatch.objects.filter(expiration_date__lt=yesterday).count()
    expiring_soon_yesterday = SupplyBatch.objects.filter(expiration_date__range=(yesterday, today + timedelta(days=6))).count()

    # Variações
    total_items_variation, total_items_positive = calc_variation(total_items, total_items_yesterday)
    total_active_variation, total_active_positive = calc_variation(total_active, total_active_yesterday)
    total_expired_variation, total_expired_positive = calc_variation(total_expired, total_expired_yesterday)
    expiring_soon_variation, expiring_soon_positive = calc_variation(expiring_soon, expiring_soon_yesterday)

    # Categorias (para gráfico de barras)
    category_labels = []
    category_counts = []
    for cat in SupplyItem.objects.values("category").annotate(count=Count("id")).order_by("-count"):
        label = SupplyCategory(cat["category"]).label if cat["category"] else "Indefinido"
        category_labels.append(label)
        category_counts.append(cat["count"])

    # Linha do tempo (timeline)
    timeline_labels = []
    timeline_data = []
    timeline_colors = []
    timeline_sizes = []

    timeline_raw = (
        SupplyBatch.objects
        .values("expiration_date")
        .annotate(count=Count("id"), total_quantity=Sum("quantity"))
        .order_by("expiration_date")
    )

    for entry in timeline_raw:
        exp_date = entry["expiration_date"]
        label = date_format(exp_date, "d M Y")
        count = entry["count"]
        total_units = entry["total_quantity"] or 1

        timeline_labels.append(label)
        timeline_data.append(count)
        timeline_sizes.append(float(total_units))

        if exp_date < today:
            timeline_colors.append("#e74a3b")
        elif today <= exp_date <= next_7_days:
            timeline_colors.append("#f6c23e")
        else:
            timeline_colors.append("#155724")

    # Garantir inclusão das datas de referência
    base_dates = [today, today - timedelta(days=7), today - timedelta(days=15)]
    base_labels = [date_format(d, "d M Y") for d in base_dates]

    for label in base_labels:
        if label not in timeline_labels:
            timeline_labels.append(label)
            timeline_data.append(0)
            timeline_sizes.append(0.0)
            timeline_colors.append("#dee2e6")  # cinza claro para neutros

    # Ordenar os dados cronologicamente
    def parse_date(label):
        try:
            return datetime.strptime(label, "%d %b %Y")
        except:
            return datetime(1900, 1, 1)

    zipped = list(zip(timeline_labels, timeline_data, timeline_sizes, timeline_colors))
    zipped.sort(key=lambda x: parse_date(x[0]))
    timeline_labels, timeline_data, timeline_sizes, timeline_colors = zip(*zipped)

    # Datas de referência para anotações no gráfico
    today_label = date_format(today, "d M Y")
    minus7_label = date_format(today - timedelta(days=7), "d M Y")
    minus15_label = date_format(today - timedelta(days=15), "d M Y")

    context = {
        "total_items": total_items,
        "total_active": total_active,
        "total_expired": total_expired,
        "expiring_soon": expiring_soon,
        "total_valid": total_valid,

        # Variações
        "total_items_variation_text": total_items_variation,
        "total_items_variation_positive": total_items_positive,
        "total_active_variation_text": total_active_variation,
        "total_active_variation_positive": total_active_positive,
        "total_expired_variation_text": total_expired_variation,
        "total_expired_variation_positive": total_expired_positive,
        "expiring_soon_variation_text": expiring_soon_variation,
        "expiring_soon_variation_positive": expiring_soon_positive,

        # Gráficos
        "category_labels": json.dumps(category_labels),
        "category_counts": json.dumps(category_counts),
        "doughnut_labels": json.dumps(['Válidos', 'Próximos', 'Vencidos']),
        "doughnut_data": json.dumps([total_valid, expiring_soon, total_expired]),
        "doughnut_colors": json.dumps(['#1cc88a', '#f6c23e', '#e74a3b']),
        "bar_colors": json.dumps(['#4e73df', '#36b9cc', '#f6c23e', '#1cc88a', '#e74a3b']),
        "timeline_labels": json.dumps(timeline_labels),
        "timeline_data": json.dumps(timeline_data),
        "timeline_colors": json.dumps(timeline_colors),
        "timeline_sizes": json.dumps(timeline_sizes),

        # Linhas de referência
        "today_label": date_format(today, "d M Y"),
        "minus7_label": minus7_label,
        "minus15_label": minus15_label,
    }

    return render(request, "admin/supplies/dashboard.html", context)
