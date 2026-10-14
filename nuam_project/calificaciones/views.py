import csv
import io
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import CalificacionTributaria, FactorTributario, AuditoriaLog
from .services import calcular_factores_desde_montos

# Create your views here.

def mantenedor_calificaciones(request):
    """Vista principal con grilla y filtros de búsqueda."""
    query = CalificacionTributaria.objects.select_related('factores').all()

    mercado = request.GET.get('mercado')
    origen = request.GET.get('origen')
    ejercicio = request.GET.get('ejercicio')

    if mercado:
        query = query.filter(mercado=mercado)
    if origen:
        query = query.filter(origen=origen)
    if ejercicio:
        query = query.filter(ejercicio=ejercicio)

    context = {
        'calificaciones': query,
        'mercado_sel': mercado or '',
        'origen_sel': origen or '',
        'ejercicio_sel': ejercicio or '',
    }
    return render(request, 'calificaciones/mantenedor.html', context)


def guardar_calificacion(request):
    """Crea o edita una calificación tributaria individual con cálculo automático."""
    if request.method == 'POST':
        calificacion_id = request.POST.get('calificacion_id')
        try:
            ejercicio = int(request.POST['ejercicio'])
            mercado = request.POST['mercado']
            instrumento = request.POST['instrumento']
            secuencia_evento = int(request.POST['secuencia_evento'])
            fecha_pago = request.POST['fecha_pago']
            descripcion = request.POST['descripcion']
            acogido_isfut = request.POST.get('acogido_isfut') == 'on'
            tipo_sociedad = request.POST.get('tipo_sociedad', 'A')

            if secuencia_evento <= 10000:
                messages.error(request, "La secuencia de evento debe ser superior a 10.000.")
                return redirect('mantenedor')

            montos = {}
            for i in range(8, 38):
                montos[f'monto_{i:02d}'] = request.POST.get(f'monto_{i:02d}', '0')

            factores = calcular_factores_desde_montos(montos)

            if calificacion_id:
                calif = get_object_or_404(CalificacionTributaria, id=calificacion_id)
                accion = 'MODIFICACION'
            else:
                calif = CalificacionTributaria()
                accion = 'CREACION'

            calif.ejercicio = ejercicio
            calif.mercado = mercado
            calif.instrumento = instrumento
            calif.secuencia_evento = secuencia_evento
            calif.fecha_pago = fecha_pago
            calif.descripcion = descripcion
            calif.acogido_isfut = acogido_isfut
            calif.tipo_sociedad = tipo_sociedad
            calif.origen = 'CORREDOR'
            calif.save()

            factor_obj, _ = FactorTributario.objects.get_or_create(calificacion=calif)
            for k, v in factores.items():
                setattr(factor_obj, k, v)
            factor_obj.save()

            AuditoriaLog.objects.create(
                calificacion_id=calif.id,
                instrumento=calif.instrumento,
                usuario=request.user.username or 'admin_corredor',
                accion=accion,
                origen='MANUAL',
                detalles={'secuencia': secuencia_evento, 'factores': {k: str(v) for k, v in factores.items()}}
            )

            messages.success(request, f"Calificación de {instrumento} guardada correctamente con factores calculados.")
        except ValueError as err:
            messages.error(request, str(err))
        except Exception as e:
            messages.error(request, f"Error al procesar el registro: {e}")

    return redirect('mantenedor')


def eliminar_calificacion(request, calificacion_id):
    """Elimina una calificación individual conservando el registro de auditoría."""
    calif = get_object_or_404(CalificacionTributaria, id=calificacion_id)
    instrumento = calif.instrumento
    AuditoriaLog.objects.create(
        calificacion_id=calif.id,
        instrumento=instrumento,
        usuario=request.user.username or 'admin_corredor',
        accion='ELIMINACION',
        origen='MANUAL',
        detalles={'ejercicio': calif.ejercicio, 'secuencia': calif.secuencia_evento}
    )
    calif.delete()
    messages.success(request, f"Calificación de {instrumento} eliminada exitosamente.")
    return redirect('mantenedor')


def carga_masiva_csv(request):
    """Procesa un archivo CSV con calificaciones masivas."""
    if request.method == 'POST' and request.FILES.get('archivo_csv'):
        archivo = request.FILES['archivo_csv']
        if not archivo.name.endswith('.csv'):
            messages.error(request, "El archivo debe tener formato .CSV")
            return redirect('mantenedor')

        try:
            datos = archivo.read().decode('utf-8-sig')
            lineas = csv.DictReader(io.StringIO(datos))
            procesados = 0

            for fila in lineas:
                calif, _ = CalificacionTributaria.objects.update_or_create(
                    ejercicio=int(fila['ejercicio']),
                    mercado=fila['mercado'].strip(),
                    instrumento=fila['instrumento'].strip(),
                    secuencia_evento=int(fila['secuencia']),
                    origen='CSV',
                    defaults={
                        'fecha_pago': fila['fecha'],
                        'numero_dividendo': int(fila.get('dividendo', 0)),
                        'tipo_sociedad': fila.get('tipo_sociedad', 'A'),
                        'descripcion': fila.get('descripcion', 'Carga Masiva CSV'),
                        'valor_historico': Decimal(fila.get('valor_historico', '0')),
                    }
                )

                factor_obj, _ = FactorTributario.objects.get_or_create(calificacion=calif)
                for i in range(8, 38):
                    col = f'factor_{i:02d}'
                    if col in fila:
                        setattr(factor_obj, col, Decimal(fila[col]))
                factor_obj.save()
                procesados += 1

            AuditoriaLog.objects.create(
                instrumento="CARGA_LOTE",
                usuario=request.user.username or 'admin_corredor',
                accion='CARGA_MASIVA',
                origen='CSV',
                detalles={'total_registros': procesados, 'archivo': archivo.name}
            )
            messages.success(request, f"Se procesaron {procesados} calificaciones exitosamente desde el archivo CSV.")
        except Exception as e:
            messages.error(request, f"Error en la estructura del archivo CSV: {e}")

    return redirect('mantenedor')