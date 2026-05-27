import requests
import json
from django.conf import settings
from django.core.cache import cache

class FonnteService:
    """Service untuk mengirim WhatsApp menggunakan Fonnte API"""
    
    def __init__(self):
        self.api_key = settings.FONNTE_API_KEY
        self.base_url = settings.FONNTE_BASE_URL
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def send_message(self, phone_number, message):
        """
        Kirim pesan teks ke nomor WhatsApp
        
        Args:
            phone_number (str): Nomor tujuan (format: 628xxxxxxxxx)
            message (str): Pesan yang akan dikirim
        
        Returns:
            dict: Response dari API
        """
        # Format nomor telepon (hapus '+' jika ada, pastikan 62)
        phone_number = self._format_phone_number(phone_number)
        
        data = {
            'target': phone_number,
            'message': message,
            'countryCode': '62'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/send",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"WA sent to {phone_number}: {result}")
                return {'success': True, 'data': result}
            else:
                print(f"WA failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
                
        except requests.exceptions.RequestException as e:
            print(f"WA request error: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_template_taaruf(self, phone_number, name):
        """Kirim template pesan ta'aruf"""
        message = f"""*Assalamu'alaikum {name},*

Terima kasih telah mendaftar di Program Ta'aruf AsuhBijak.

✅ Pendaftaran Anda telah kami terima.
📋 Tim mediator kami akan menghubungi Anda dalam 1x24 jam untuk verifikasi data dan sesi profiling.

*Yang perlu disiapkan:*
1. Foto KTP/SIM
2. Biodata lengkap
3. Surat izin dari wali (jika diperlukan)

Untuk informasi lebih lanjut, silahkan hubungi:
📞 Hotline: 0812-3456-7890
📧 Email: taaruf@asuhbijak.com

Jazakallah khair,
*Tim AsuhBijak Ta'aruf* 🤝
"""
        return self.send_message(phone_number, message)
    
    def send_template_konsultasi(self, phone_number, name, psychologist, date, time, method):
        """Kirim template pesan konsultasi"""
        method_names = {
            'video': 'Video Call (Zoom/Google Meet)',
            'chat': 'Chat Konsultasi',
            'telepon': 'Telepon'
        }
        
        message = f"""*Halo {name},*

Booking konsultasi Anda telah kami terima!

📋 *Detail Konsultasi:*
👨‍⚕️ Psikolog: {psychologist}
📅 Tanggal: {date}
⏰ Waktu: {time}
💬 Metode: {method_names.get(method, method)}

*Langkah Selanjutnya:*
1️⃣ Tim kami akan mengirimkan link konsultasi H-1 sesi
2️⃣ Pastikan Anda berada di tempat yang tenang
3️⃣ Siapkan daftar pertanyaan yang ingin didiskusikan

*Biaya:*
💰 Silahkan melakukan pembayaran sebelum sesi dimulai
💳 Transfer ke: BCA 1234567890 a.n AsuhBijak

Untuk membatalkan/reschedule, hubungi kami minimal H-1.

Terima kasih,
*Tim AsuhBijak Konsultasi* 🌿
"""
        return self.send_message(phone_number, message)
    
    def send_payment_confirmation(self, phone_number, name, amount):
        """Kirim konfirmasi pembayaran"""
        message = f"""*Halo {name},*

✅ Pembayaran sebesar Rp{amount:,.0f} telah kami terima.

Terima kasih atas kepercayaan Anda menggunakan layanan AsuhBijak. Kami akan segera memproses layanan Anda.

*Info lebih lanjut:*
📞 WA: 0812-3456-7890
📧 Email: hello@asuhbijak.com

Salam hangat,
*Tim AsuhBijak*
"""
        return self.send_message(phone_number, message)
    
    def send_reminder(self, phone_number, name, service, datetime):
        """Kirim pengingat jadwal"""
        message = f"""*Pengingat Jadwal {service} AsuhBijak*

Halo {name},

Jadwal {service} Anda akan dilaksanakan pada:
📅 {datetime}

Mohon hadir tepat waktu.

Terima kasih,
*Tim AsuhBijak*
"""
        return self.send_message(phone_number, message)
    
    def _format_phone_number(self, phone_number):
        """Format nomor telepon ke format yang benar untuk Fonnte"""
        # Hapus semua karakter non-digit
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # Jika dimulai dengan 0, ganti dengan 62
        if phone.startswith('0'):
            phone = '62' + phone[1:]
        # Jika dimulai dengan 62, biarkan
        elif phone.startswith('62'):
            pass
        # Jika dimulai dengan 8, tambahkan 62
        elif phone.startswith('8'):
            phone = '62' + phone
        
        return phone

# Instance global
wa_service = FonnteService()


def send_whatsapp_notification(phone_number, name, notification_type, **kwargs):
    """
    Fungsi helper untuk mengirim notifikasi WhatsApp
    
    Args:
        phone_number (str): Nomor tujuan
        name (str): Nama penerima
        notification_type (str): Jenis notifikasi ('taaruf', 'konsultasi', 'payment', 'reminder')
        **kwargs: Parameter tambahan sesuai jenis notifikasi
    """
    if notification_type == 'taaruf':
        return wa_service.send_template_taaruf(phone_number, name)
    
    elif notification_type == 'konsultasi':
        return wa_service.send_template_konsultasi(
            phone_number, 
            name,
            kwargs.get('psychologist', ''),
            kwargs.get('date', ''),
            kwargs.get('time', ''),
            kwargs.get('method', '')
        )
    
    elif notification_type == 'payment':
        return wa_service.send_payment_confirmation(phone_number, name, kwargs.get('amount', 0))
    
    elif notification_type == 'reminder':
        return wa_service.send_reminder(phone_number, name, kwargs.get('service', ''), kwargs.get('datetime', ''))
    
    return {'success': False, 'error': 'Unknown notification type'}


def send_bulk_whatsapp(phone_numbers, message):
    """Kirim pesan ke banyak nomor"""
    results = []
    for phone in phone_numbers:
        result = wa_service.send_message(phone, message)
        results.append(result)
    return results


# apps/core/wa_service.py - Tambahkan method ini

def send_template_checkout(self, phone_number, name, kelas_nama, order_id, harga, payment_url):
    """Kirim template pesan checkout dengan Midtrans payment link"""
    message = f"""*🛒 KONFIRMASI ORDER KELAS ASUHBIJAK*

Halo *{name}*,

Terima kasih telah melakukan pemesanan kelas!

📚 *Detail Kelas:*
━━━━━━━━━━━━━━━━━━━━━
🎓 Kelas: {kelas_nama}
💰 Harga: Rp{harga:,.0f}
🆔 Order ID: {order_id}
━━━━━━━━━━━━━━━━━━━━━

💳 *INFORMASI PEMBAYARAN:*

🔗 *Link Pembayaran Midtrans:*
{payment_url}

Klik link di atas untuk menyelesaikan pembayaran.

Metode pembayaran yang tersedia:
✅ Kartu Kredit (Visa/Mastercard)
✅ Transfer Bank (BCA, Mandiri, BNI, BRI)
✅ QRIS
✅ GoPay
✅ Alfamart / Indomaret

⏰ *Batas Pembayaran:*
24 jam setelah order dibuat

*Langkah Selanjutnya:*
1️⃣ Klik link pembayaran di atas
2️⃣ Pilih metode pembayaran yang tersedia
3️⃣ Lakukan pembayaran sesuai instruksi
4️⃣ Akses kelas akan otomatis aktif setelah pembayaran sukses

🔒 *Keamanan:*
Pembayaran diproses oleh Midtrans (gateway resmi terpercaya)

Terima kasih sudah belajar di AsuhBijak!
*Tim AsuhBijak* 🌿
"""
    return self.send_message(phone_number, message)
