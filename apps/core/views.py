from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import uuid
import json
import requests

from datetime import datetime
from .models import Artikel, PendaftaranTaaruf, Subscriber, BookingKonsultasi, KelasOrder
from .midtrans_payment import midtrans_payment, get_midtrans_status

from .wa_service import send_whatsapp_notification
# apps/core/views.py - Tambahkan fungsi ini

# Data kelas (bisa dipindahkan ke database nanti)
# Data kelas
KELAS_DATA = {
    1: {'id': 1, 'nama': 'Positive Discipline 101', 'harga': 149000, 'harga_asli': 299000, 'durasi': '8 jam', 'modul': 5, 'kategori': 'parenting', 'deskripsi': 'Pelajari disiplin positif tanpa hukuman...'},
    2: {'id': 2, 'nama': 'Memahami Dunia Anak (Psikologi Perkembangan)', 'harga': 189000, 'harga_asli': 350000, 'durasi': '10 jam', 'modul': 6, 'kategori': 'psikologi', 'deskripsi': 'Memetakan tahap tumbuh kembang anak...'},
    3: {'id': 3, 'nama': 'Art of Active Listening', 'harga': 99000, 'harga_asli': 189000, 'durasi': '5 jam', 'modul': 4, 'kategori': 'komunikasi', 'deskripsi': 'Tingkatkan kualitas komunikasi...'},
    4: {'id': 4, 'nama': 'Ta\'aruf & Visi Keluarga Sakinah', 'harga': 149000, 'harga_asli': 279000, 'durasi': '6 jam', 'modul': 4, 'kategori': 'pranikah', 'deskripsi': 'Panduan ta\'aruf syar\'i...'},
    5: {'id': 5, 'nama': 'Mendidik Remaja Zaman Now', 'harga': 129000, 'harga_asli': 249000, 'durasi': '7 jam', 'modul': 5, 'kategori': 'parenting', 'deskripsi': 'Strategi menghadapi remaja...'},
    6: {'id': 6, 'nama': 'Emotional Intelligence untuk Anak', 'harga': 159000, 'harga_asli': 299000, 'durasi': '6 jam', 'modul': 4, 'kategori': 'psikologi', 'deskripsi': 'Mengajarkan anak mengelola emosi...'},
}

def kelas(request):
    """Halaman daftar kelas"""
    kelas_data = list(KELAS_DATA.values())
    return render(request, 'core/kelas.html', {'kelas_data': kelas_data})

def kelas_detail(request, kelas_id):
    """Halaman detail kelas"""
    if kelas_id not in KELAS_DATA:
        messages.error(request, 'Kelas tidak ditemukan')
        return redirect('core:kelas')
    
    kelas = KELAS_DATA[kelas_id]
    context = {
        'kelas': kelas,
    }
    return render(request, 'core/kelas_detail.html', context)


def index(request):
    """Halaman beranda"""
    artikel_terbaru = Artikel.objects.all().order_by('-created_at')[:4]  # Ambil 4 artikel terbaru
    context = {
        'artikel_terbaru': artikel_terbaru,
    }
    return render(request, 'core/index.html', context)

def artikel_list(request):
    """Halaman daftar artikel"""
    artikel_list = Artikel.objects.all().order_by('-created_at')
    kategori = request.GET.get('kategori')
    if kategori:
        artikel_list = artikel_list.filter(kategori=kategori)
    
    context = {
        'artikel_list': artikel_list,
        'kategori_aktif': kategori,
    }
    return render(request, 'core/artikel.html', context)

def artikel_detail(request, slug):
    artikel = get_object_or_404(Artikel, slug=slug)
    
    # Hitung estimasi menit membaca untuk artikel utama (jumlah kata / 200)
    word_count = len(artikel.konten.split()) if artikel.konten else 0
    menit_membaca = max(1, word_count // 200)
    
    # Tambahkan hitungan dibaca
    artikel.dibaca += 1
    artikel.save(update_fields=['dibaca'])
    
    # Ambil artikel terkait dengan kategori yang sama (kecuali artikel ini sendiri)
    related_queryset = Artikel.objects.filter(kategori=artikel.kategori).exclude(id=artikel.id)[:3]
    
    # Proses estimasi membaca untuk masing-masing artikel terkait
    related_articles = []
    for rel in related_queryset:
        rel_word_count = len(rel.konten.split()) if rel.konten else 0
        rel_menit = max(1, rel_word_count // 200)
        
        # Pasang atribut dinamis ke objek objek terkait
        rel.menit_membaca = rel_menit
        related_articles.append(rel)
    
    context = {
        'artikel': artikel,
        'menit_membaca': menit_membaca,
        'related_articles': related_articles,
    }
    return render(request, 'core/artikel_detail.html', context)

def taaruf(request):
    """Halaman pendaftaran ta'aruf"""
    if request.method == 'POST':
        nama_lengkap = request.POST.get('nama_lengkap')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir') or None
        domisili = request.POST.get('domisili', '')
        email = request.POST.get('email')
        whatsapp = request.POST.get('whatsapp')
        pekerjaan = request.POST.get('pekerjaan', '')
        pendidikan = request.POST.get('pendidikan', '')
        kriteria = request.POST.get('kriteria', '')
        
        # Simpan ke database
        pendaftaran = PendaftaranTaaruf.objects.create(
            nama_lengkap=nama_lengkap,
            jenis_kelamin=jenis_kelamin,
            tanggal_lahir=tanggal_lahir,
            domisili=domisili,
            email=email,
            whatsapp=whatsapp,
            pekerjaan=pekerjaan,
            pendidikan=pendidikan,
            kriteria_pasangan=kriteria,
        )
        
        # Kirim notifikasi WhatsApp via Fonnte
        wa_result = send_whatsapp_notification(
            whatsapp, 
            nama_lengkap, 
            'taaruf'
        )
        
        # Update status notifikasi
        if wa_result.get('success'):
            pendaftaran.wa_notification_sent = True
            pendaftaran.save()
        
        # Kirim email notifikasi
        try:
            send_mail(
                'Konfirmasi Pendaftaran Ta\'aruf - AsuhBijak',
                f'Halo {nama_lengkap},\n\nTerima kasih telah mendaftar program ta\'aruf AsuhBijak. Tim kami akan menghubungi Anda dalam 1x24 jam.\n\nSalam hangat,\nTim AsuhBijak',
                settings.DEFAULT_FROM_EMAIL or 'noreply@asuhbijak.com',
                [email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email error: {e}")
        
        messages.success(request, 'Pendaftaran ta\'aruf berhasil! Silahkan cek WhatsApp untuk info selanjutnya.')
        return redirect('core:taaruf')
    
    return render(request, 'core/taaruf.html')

def kelas(request):
    """Halaman kelas online"""
    kelas_data = [
        {'id': 1, 'nama': 'Positive Discipline 101', 'harga': 149000, 'harga_asli': 299000, 'durasi': '8 jam', 'modul': 5, 'kategori': 'parenting'},
        {'id': 2, 'nama': 'Memahami Dunia Anak (Psikologi Perkembangan)', 'harga': 189000, 'harga_asli': 350000, 'durasi': '10 jam', 'modul': 6, 'kategori': 'psikologi'},
        {'id': 3, 'nama': 'Art of Active Listening', 'harga': 99000, 'harga_asli': 189000, 'durasi': '5 jam', 'modul': 4, 'kategori': 'komunikasi'},
        {'id': 4, 'nama': 'Ta\'aruf & Visi Keluarga Sakinah', 'harga': 149000, 'harga_asli': 279000, 'durasi': '6 jam', 'modul': 4, 'kategori': 'pranikah'},
        {'id': 5, 'nama': 'Mendidik Remaja Zaman Now', 'harga': 129000, 'harga_asli': 249000, 'durasi': '7 jam', 'modul': 5, 'kategori': 'parenting'},
        {'id': 6, 'nama': 'Emotional Intelligence untuk Anak', 'harga': 159000, 'harga_asli': 299000, 'durasi': '6 jam', 'modul': 4, 'kategori': 'psikologi'},
    ]
    return render(request, 'core/kelas.html', {'kelas_data': kelas_data})


def konsultasi(request):
    """Halaman booking konsultasi"""
    if request.method == 'POST':
        nama = request.POST.get('nama')
        email = request.POST.get('email')
        whatsapp = request.POST.get('whatsapp')
        psikolog = request.POST.get('psikolog')
        tanggal = request.POST.get('tanggal')
        waktu = request.POST.get('waktu')
        topik = request.POST.get('topik', '')
        metode = request.POST.get('metode', 'video')
        
        # Simpan ke database
        booking = BookingKonsultasi.objects.create(
            nama=nama,
            email=email,
            whatsapp=whatsapp,
            psikolog=psikolog,
            tanggal=tanggal,
            waktu=waktu,
            topik=topik,
            metode=metode,
        )
        
        # Kirim WhatsApp konfirmasi via Fonnte
        wa_result = send_whatsapp_notification(
            whatsapp,
            nama,
            'konsultasi',
            psychologist=psikolog,
            date=tanggal,
            time=waktu,
            method=metode
        )
        
        if wa_result.get('success'):
            booking.wa_notification_sent = True
            booking.save()
        
        # Kirim email konfirmasi
        try:
            send_mail(
                'Konfirmasi Booking Konsultasi - AsuhBijak',
                f'Halo {nama},\n\nBooking konsultasi Anda telah kami terima.\n\nDetail:\nPsikolog: {psikolog}\nTanggal: {tanggal}\nWaktu: {waktu}\n\nTim kami akan menghubungi Anda via WhatsApp untuk konfirmasi.\n\nSalam,\nTim AsuhBijak',
                settings.DEFAULT_FROM_EMAIL or 'noreply@asuhbijak.com',
                [email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email error: {e}")
        
        messages.success(request, 'Booking konsultasi berhasil! Silahkan cek WhatsApp untuk info selanjutnya.')
        return redirect('core:konsultasi')
    
    return render(request, 'core/konsultasi.html')

def subscribe_newsletter(request):
    """Subscribe newsletter"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            subscriber, created = Subscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, 'Berlangganan newsletter berhasil!')
            else:
                messages.info(request, 'Email sudah terdaftar.')
        else:
            messages.error(request, 'Email tidak valid.')
        return redirect(request.META.get('HTTP_REFERER', 'core:index'))
    return redirect('core:index')



def checkout(request, kelas_id):
    """Halaman checkout kelas"""
    if kelas_id not in KELAS_DATA:
        messages.error(request, 'Kelas tidak ditemukan')
        return redirect('core:kelas')
    
    kelas = KELAS_DATA[kelas_id]
    
    if request.method == 'POST':
        nama = request.POST.get('nama')
        email = request.POST.get('email')
        whatsapp = request.POST.get('whatsapp')
        
        # Validasi
        if not all([nama, email, whatsapp]):
            messages.error(request, 'Harap isi semua data yang diperlukan')
            return redirect('core:checkout', kelas_id=kelas_id)
        
        # Generate Order ID
        order_id = f"FML-{uuid.uuid4().hex[:8].upper()}"
        
        # Simpan order - PASTIKAN USER TERSIMPAN
        order = KelasOrder.objects.create(
            order_id=order_id,
            kelas_id=kelas_id,
            kelas_nama=kelas['nama'],
            kelas_harga=kelas['harga'],
            nama=nama,
            email=email,
            whatsapp=whatsapp,
            payment_method='midtrans',
            payment_gateway='midtrans',
            expires_at=timezone.now() + timedelta(hours=24),
            user=request.user if request.user.is_authenticated else None  # ← PENTING!
        )
        
        # Buat transaksi di Midtrans
        result = midtrans_payment.create_transaction(order)
        
        if result['success']:
            order.payment_token = result['token']
            order.payment_url = result['redirect_url']
            order.save()
            
            send_whatsapp_notification(
                whatsapp, nama, 'checkout',
                kelas_nama=kelas['nama'],
                order_id=order_id,
                harga=kelas['harga'],
                payment_url=result['redirect_url']
            )
            
            return redirect(result['redirect_url'])
        else:
            messages.error(request, f'Gagal memproses pembayaran: {result["error"]}')
            return redirect('core:checkout', kelas_id=kelas_id)
    
    context = {
        'kelas': kelas,
        'user': request.user if request.user.is_authenticated else None,
        'midtrans_status': get_midtrans_status(),
        'midtrans_client_key': settings.MIDTRANS_CLIENT_KEY,
        'midtrans_is_production': settings.MIDTRANS_IS_PRODUCTION
    }
    return render(request, 'core/checkout.html', context)

@csrf_exempt
def midtrans_notification(request):
    """Webhook handler untuk Midtrans notification"""
    if request.method == 'POST':
        try:
            # Parse notification data
            notification_data = json.loads(request.body)
            
            # Handle notification
            result = midtrans_payment.handle_notification(notification_data)
            
            if result['status'] == 'success':
                order_id = result['order_id']
                # Extract original order_id (ASUH-xxx-xxx)
                # Cari order berdasarkan transaction_id
                try:
                    order = KelasOrder.objects.get(transaction_id=order_id)
                    order.status = 'paid'
                    order.save()
                    
                    # Kirim WhatsApp sukses
                    send_whatsapp_notification(
                        order.whatsapp, order.nama, 'payment_success',
                        kelas_nama=order.kelas_nama,
                        order_id=order.order_id
                    )
                    
                    return JsonResponse({'status': 'ok'})
                except KelasOrder.DoesNotExist:
                    # Coba cari berdasarkan order_id asli
                    try:
                        order = KelasOrder.objects.get(order_id=order_id)
                        order.status = 'paid'
                        order.save()
                        return JsonResponse({'status': 'ok'})
                    except KelasOrder.DoesNotExist:
                        pass
            
            return JsonResponse({'status': 'ok'})
            
        except Exception as e:
            print(f"Midtrans Notification Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)



def payment_success(request, order_id):
    """Halaman sukses pembayaran"""
    try:
        order = KelasOrder.objects.get(order_id=order_id)
    except KelasOrder.DoesNotExist:
        try:
            order = KelasOrder.objects.get(transaction_id=order_id)
        except KelasOrder.DoesNotExist:
            messages.error(request, 'Order tidak ditemukan')
            return redirect('core:kelas')
    
    # Update status jika masih pending
    if order.status == 'pending':
        order.status = 'paid'
        
        # 🔥 PENTING: Hubungkan order dengan user yang login
        if request.user.is_authenticated and not order.user:
            order.user = request.user
            print(f"User {request.user.username} linked to order {order.order_id}")
        
        order.save()
        
        # Kirim WhatsApp sukses
        send_whatsapp_notification(
            order.whatsapp, order.nama, 'payment_success',
            kelas_nama=order.kelas_nama,
            order_id=order.order_id
        )
        
        messages.success(request, f'✅ Pembayaran berhasil! Kelas {order.kelas_nama} telah ditambahkan ke "Kelas Saya".')
    
    return render(request, 'core/payment_success.html', {'order': order})

def payment_failed(request, order_id):
    """Halaman gagal pembayaran"""
    order = get_object_or_404(KelasOrder, order_id=order_id)
    return render(request, 'core/payment_failed.html', {'order': order})


@login_required
def my_classes(request):
    """Halaman kelas yang sudah dibeli user"""
    # Ambil semua order dengan status paid milik user yang login
    orders = KelasOrder.objects.filter(
        user=request.user,
        status='paid'
    ).order_by('-created_at')
    
    print(f"User: {request.user.username}")
    print(f"Total orders found: {orders.count()}")
    for order in orders:
        print(f"  - {order.kelas_nama} ({order.status})")
    
    return render(request, 'core/my_classes.html', {'orders': orders})
