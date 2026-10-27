import io
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

import numpy as np
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw

from . import doc_scan, identity_docs
from .models import Employee, IdentityDocument, PushSubscription


def phone_photo(with_card=True):
    """Foto simulata: tessera chiara inclinata su un tavolo scuro."""
    import cv2
    w, h = 1500, 2000
    bg = np.full((h, w, 3), (90, 100, 110), np.uint8)
    if with_card:
        card = Image.new('RGB', (856, 540), (235, 240, 250))
        d = ImageDraw.Draw(card)
        d.rectangle([40, 60, 240, 320], fill=(180, 195, 220))
        d.text((300, 80), 'ESEMPIO', fill=(30, 50, 90))
        src = np.float32([[0, 0], [855, 0], [855, 539], [0, 539]])
        dst = np.float32([[250, 700], [1250, 640], [1300, 1330], [200, 1300]])
        m = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(np.array(card), m, (w, h))
        mask = cv2.warpPerspective(np.full((540, 856), 255, np.uint8), m, (w, h))
        bg[mask > 0] = warped[mask > 0]
    buf = io.BytesIO()
    Image.fromarray(bg).save(buf, 'JPEG', quality=85)
    return buf.getvalue()


class ScanTests(TestCase):
    def test_card_is_cropped_to_id1(self):
        out, cropped = doc_scan.process_photo(phone_photo())
        self.assertTrue(cropped)
        self.assertEqual(Image.open(io.BytesIO(out)).size, (doc_scan.OUT_W, doc_scan.OUT_H))

    def test_no_card_keeps_original(self):
        out, cropped = doc_scan.process_photo(phone_photo(with_card=False))
        self.assertFalse(cropped)

    def test_invalid_file(self):
        with self.assertRaises(doc_scan.ScanError):
            doc_scan.process_photo(b'non una foto')


@override_settings(PUSH_ASYNC=False)
class IdentityDocumentFlowTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        ov = override_settings(MEDIA_ROOT=self.media, STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': self.media}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        })
        ov.enable()
        self.addCleanup(ov.disable)
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi',
                                           must_change_password=False, privacy_accepted=True)
        other = User.objects.create_user('luigi', password='x')
        Employee.objects.create(user=other, first_name='Luigi', last_name='Verdi', must_change_password=False, privacy_accepted=True)

    def _upload(self, kind='ci', expiry=None, **extra):
        expiry = expiry or (timezone.localdate() + timedelta(days=900)).isoformat()
        data = {'front': SimpleUploadedFile('f.jpg', phone_photo(), 'image/jpeg'),
                'back': SimpleUploadedFile('b.jpg', phone_photo(), 'image/jpeg'),
                'expiry_date': expiry}
        data.update(extra)
        return self.client.post(reverse('employee_document_upload', args=[kind]), data)

    def test_employee_uploads_and_admin_approves(self):
        self.client.login(username='mario', password='x')
        self.assertContains(self.client.get(reverse('employee_documents')), "Carta d&#x27;identità")
        self.assertContains(self.client.get(reverse('employee_document_upload', args=['ci'])), 'Inizia: fotografa il fronte')
        r = self._upload()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()['ok'])
        doc = IdentityDocument.objects.get()
        self.assertEqual(doc.status, 'pending')
        self.assertTrue(doc.front_cropped and doc.back_cropped)
        self.assertContains(self.client.get(reverse('employee_documents')), 'In verifica')
        self.assertEqual(self.client.get(reverse('document_image', args=[doc.id, 'fronte']))['Content-Type'], 'image/jpeg')

        self.client.login(username='admin', password='x')
        self.assertContains(self.client.get(reverse('admin_documents') + '?filtro=verificare'), 'Rossi')
        self.client.post(reverse('admin_document_detail', args=[doc.id]), {'action': 'approve', 'expiry_date': doc.expiry_date.isoformat()})
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'approved')
        pdf = self.client.get(reverse('admin_document_pdf', args=[doc.id]))
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_validation(self):
        self.client.login(username='mario', password='x')
        past = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertIn('scaduto', self._upload(expiry=past).json()['error'])
        r = self.client.post(reverse('employee_document_upload', args=['ci']), {'expiry_date': '2030-01-01'})
        self.assertIn('fronte e retro', r.json()['error'])
        r = self._upload(front=SimpleUploadedFile('f.jpg', b'xx', 'image/jpeg'))
        self.assertFalse(r.json()['ok'])
        self.assertEqual(self.client.get(reverse('employee_document_upload', args=['passaporto'])).status_code, 404)
        self.assertFalse(IdentityDocument.objects.exists())

    def test_permissions(self):
        self.client.login(username='mario', password='x')
        self._upload()
        doc = IdentityDocument.objects.get()
        self.assertEqual(self.client.get(reverse('admin_document_pdf', args=[doc.id])).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin_documents')).status_code, 302)
        self.client.login(username='luigi', password='x')
        self.assertEqual(self.client.get(reverse('document_image', args=[doc.id, 'fronte'])).status_code, 403)

    def test_reject_requires_note_and_notifies(self):
        self.client.login(username='mario', password='x')
        self._upload()
        doc = IdentityDocument.objects.get()
        self.client.login(username='admin', password='x')
        r = self.client.post(reverse('admin_document_detail', args=[doc.id]), {'action': 'reject'})
        self.assertContains(r, 'Scrivi il motivo')
        with mock.patch('portal.push.send_to_user') as send, self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('admin_document_detail', args=[doc.id]), {'action': 'reject', 'review_note': 'foto sfocata'})
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'rejected')
        self.assertEqual(send.call_args.kwargs['title'], 'Documento da rifare')
        self.client.login(username='mario', password='x')
        page = self.client.get(reverse('employee_documents'))
        self.assertContains(page, 'Da rifare')
        self.assertContains(page, 'foto sfocata')

    def test_rotate(self):
        self.client.login(username='mario', password='x')
        self._upload()
        doc = IdentityDocument.objects.get()
        self.client.login(username='admin', password='x')
        self.client.post(reverse('admin_document_detail', args=[doc.id]), {'action': 'rotate', 'side': 'fronte', 'degrees': '90'})
        doc.refresh_from_db()
        doc.front_image.open('rb')
        self.assertEqual(Image.open(doc.front_image).size, (doc_scan.OUT_H, doc_scan.OUT_W))
        doc.front_image.close()
        r = self.client.get(reverse('document_image', args=[doc.id, 'fronte']))
        self.assertEqual(r.status_code, 200)

    def test_rotate_with_overwriting_storage(self):
        """Come lo storage online (Cloudflare R2): stesso nome = sovrascrive. La foto deve restare disponibile."""
        from django.core.files.storage import FileSystemStorage

        class OverwriteStorage(FileSystemStorage):
            def get_available_name(self, name, max_length=None):
                if self.exists(name):
                    self.delete(name)
                return name

        self.client.login(username='mario', password='x')
        self._upload()
        doc = IdentityDocument.objects.get()
        storage = OverwriteStorage(location=self.media)
        IdentityDocument._meta.get_field('front_image').storage = storage
        self.addCleanup(setattr, IdentityDocument._meta.get_field('front_image'), 'storage',
                        IdentityDocument._meta.get_field('back_image').storage)
        self.client.login(username='admin', password='x')
        for _ in range(3):
            self.client.post(reverse('admin_document_detail', args=[doc.id]), {'action': 'rotate', 'side': 'fronte', 'degrees': '90'})
            doc.refresh_from_db()
            self.assertTrue(storage.exists(doc.front_image.name), doc.front_image.name)
            self.assertEqual(self.client.get(reverse('document_image', args=[doc.id, 'fronte'])).status_code, 200)

    def test_crop_precision(self):
        """Il ritaglio segue il bordo vero della tessera (errore sugli angoli sotto lo 0,5%)."""
        import cv2
        w, h = 1500, 2000
        bg = np.full((h, w, 3), (90, 100, 110), np.uint8)
        card = np.full((540, 856, 3), (235, 240, 250), np.uint8)
        cv2.rectangle(card, (40, 60), (240, 320), (180, 195, 220), -1)
        truth = np.float32([[250, 700], [1250, 640], [1300, 1330], [200, 1300]])
        m = cv2.getPerspectiveTransform(np.float32([[0, 0], [856, 0], [856, 540], [0, 540]]), truth)
        warped = cv2.warpPerspective(card, m, (w, h)); mask = cv2.warpPerspective(np.full((540, 856), 255, np.uint8), m, (w, h))
        bg[mask > 0] = warped[mask > 0]
        img = Image.fromarray(bg)
        found = doc_scan.refine_corners(img, doc_scan.find_card(img))
        err = np.max(np.linalg.norm(found - truth, axis=1)) / np.linalg.norm(truth[1] - truth[0])
        self.assertLess(err, 0.005)

    def test_expiry_notification_once_and_dashboard_alert(self):
        self.client.login(username='mario', password='x')
        self._upload(expiry=(timezone.localdate() + timedelta(days=10)).isoformat())
        doc = IdentityDocument.objects.get()
        doc.status = 'approved'; doc.save()
        with mock.patch('portal.push.send_to_user') as send:
            self.assertEqual(identity_docs.run_expiry_notifications(), 1)
            self.assertEqual(identity_docs.run_expiry_notifications(), 0)
        self.assertEqual(send.call_count, 1)
        self.assertContains(self.client.get(reverse('dashboard')), 'in scadenza')

    def test_daily_check_runs_once_per_day(self):
        identity_docs._LAST_DAILY_CHECK = None
        with mock.patch('portal.identity_docs.run_expiry_notifications', return_value=0) as run:
            self.assertTrue(identity_docs.maybe_run_daily_checks())
            identity_docs._LAST_DAILY_CHECK = None  # simula un altro processo
            self.assertFalse(identity_docs.maybe_run_daily_checks())
        self.assertEqual(run.call_count, 1)

    def test_missing_ci_shown_on_dashboard(self):
        self.client.login(username='mario', password='x')
        self.assertContains(self.client.get(reverse('dashboard')), 'Vai ai documenti')


class CornerTests(TestCase):
    def test_corners_are_white_and_center_untouched(self):
        img = Image.new('RGB', (1712, 1080), (20, 20, 20))
        out = doc_scan.round_corners(img)
        self.assertEqual(out.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(out.getpixel((1711, 1079)), (255, 255, 255))
        self.assertEqual(out.getpixel((856, 540)), (20, 20, 20))
        self.assertEqual(out.getpixel((856, 10)), (20, 20, 20))
