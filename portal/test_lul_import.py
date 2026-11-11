import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import lul_import
from .models import Employee, Payslip



def _cf(base15):
    total = sum(lul_import._ODD[c] if i % 2 == 0 else lul_import._EVEN[c] for i, c in enumerate(base15))
    return base15 + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[total % 26]


def lul_pdf(pages):
    """pages: [(cf | None, 'COGNOME NOME', 'SETTEMBRE', '2026')]"""
    import fitz
    doc = fitz.open()
    for cf, name, month, year in pages:
        page = doc.new_page(width=595, height=842)
        page.insert_text((40, 100), 'MESE RETRIBUITO', fontsize=6)
        page.insert_text((293, 100), 'COGNOME E NOME', fontsize=6)
        page.insert_text((440, 100), 'DATA ASSUNZ.', fontsize=6)
        page.insert_text((40, 114), f'{month} {year}', fontsize=8)
        page.insert_text((293, 114), name, fontsize=8)
        page.insert_text((440, 114), '05/01/15', fontsize=8)
        page.insert_text((45, 124), 'CODICE FISCALE', fontsize=6)
        if cf:
            page.insert_text((29, 140), cf, fontsize=8)
        page.insert_text((102, 140), 'NAPOLI', fontsize=8)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class FiscalCodeTests(TestCase):
    def test_checksum(self):
        self.assertTrue(lul_import.valid_cf(_cf('RSSMRA80A01H501')))
        self.assertTrue(lul_import.valid_cf(_cf('MNCLCN65L14F83V')))  # omocodia: lettera al posto di una cifra
        good = _cf('RSSMRA80A01H501')
        bad = good[:-1] + ('A' if good[-1] != 'A' else 'B')
        self.assertFalse(lul_import.valid_cf(bad))
        self.assertFalse(lul_import.valid_cf('5134706813ABCDEF'))
        self.assertFalse(lul_import.valid_cf(''))


@override_settings(PUSH_ASYNC=False)
class LulImportTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        ov = override_settings(MEDIA_ROOT=self.media, STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': self.media}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        })
        ov.enable()
        self.addCleanup(ov.disable)
        self.cf_a, self.cf_b, self.cf_c = _cf('RSSMRA80A01H501'), _cf('VRDLGU85B02F839'), _cf('BNCNNA90C43F839')
        self.admin = User.objects.create_user('ufficio', is_staff=True)
        self.a = Employee.objects.create(user=User.objects.create_user('rossi'), first_name='Mario', last_name='Rossi', fiscal_code=self.cf_a)
        self.b = Employee.objects.create(user=User.objects.create_user('verdi'), first_name='Luigi', last_name='Verdi')
        self.other = Employee.objects.create(user=User.objects.create_user('neri'), first_name='Bruno', last_name='Neri')
        self.client.force_login(self.admin)
        self.url = reverse('admin_lul_import')
        self.pdf = lul_pdf([
            (self.cf_a, 'ROSSI MARIO', 'SETTEMBRE', '2026'),
            (self.cf_a, 'ROSSI MARIO', 'SETTEMBRE', '2026'),   # cedolino su due pagine
            (self.cf_b, 'VERDI LUIGI', 'SETTEMBRE', '2026'),   # codice fiscale non ancora registrato
            (self.cf_c, 'BIANCHI ANNA', 'SETTEMBRE', '2026'),  # non è nel portale
            (None, 'SENZA CODICE', 'SETTEMBRE', '2026'),       # pagina senza codice fiscale
        ])

    def upload(self):
        return self.client.post(self.url, {'action': 'upload', 'pdf': SimpleUploadedFile('lul.pdf', self.pdf, 'application/pdf')}, follow=True)

    def test_analysis_groups_pages_by_fiscal_code(self):
        a = lul_import.analyze(self.pdf)
        self.assertEqual(a['pages'], 5)
        groups = {g['cf']: g for g in a['groups']}
        self.assertEqual(groups[self.cf_a]['pages'], [1, 2])
        self.assertEqual(groups[self.cf_a]['name'], 'ROSSI MARIO')
        self.assertEqual((groups[self.cf_b]['month'], groups[self.cf_b]['year']), (9, 2026))
        self.assertEqual([p['page'] for p in a['loose']], [5])

    def test_preview_saves_nothing(self):
        r = self.upload()
        self.assertContains(r, 'Controlla prima di caricare')
        self.assertContains(r, 'Rossi Mario')
        self.assertFalse(Payslip.objects.exists())
        rows = {x['cf']: x for x in r.context['rows']}
        self.assertEqual(rows[self.cf_a]['status'], 'sure')
        self.assertEqual(rows[self.cf_b]['status'], 'confirm')
        self.assertEqual(rows[self.cf_b]['proposal'], self.b)
        self.assertEqual(rows[self.cf_c]['status'], 'confirm')
        self.assertIsNone(rows[self.cf_c]['proposal'])

    def test_confirm_assigns_only_certain_or_confirmed(self):
        self.upload()
        r = self.client.post(self.url, {'action': 'confirm', f'emp_{self.cf_b}': str(self.b.id), f'emp_{self.cf_c}': ''})
        self.assertEqual(r.context['done']['saved'], 2)
        self.assertEqual(r.context['done']['left_out'], 1)
        pa = Payslip.objects.get(employee=self.a)
        self.assertEqual((pa.year, pa.month), (2026, 9))
        import fitz
        pa.pdf.open('rb')
        doc = fitz.open(stream=pa.pdf.read(), filetype='pdf')
        self.assertEqual(len(doc), 2)
        self.assertTrue(all(self.cf_a in p.get_text() for p in doc))
        pb = Payslip.objects.get(employee=self.b)
        pb.pdf.open('rb')
        docb = fitz.open(stream=pb.pdf.read(), filetype='pdf')
        self.assertEqual(len(docb), 1)
        self.assertIn(self.cf_b, docb[0].get_text())
        self.b.refresh_from_db()
        self.assertEqual(self.b.fiscal_code, self.cf_b)
        self.assertFalse(Payslip.objects.filter(employee=self.other).exists())
        self.assertEqual(Payslip.objects.count(), 2)

    def test_existing_payslip_is_not_replaced_unless_asked(self):
        old = Payslip(employee=self.a, year=2026, month=9)
        old.pdf.save('vecchio.pdf', SimpleUploadedFile('v.pdf', b'%PDF-vecchio'), save=True)
        self.upload()
        r = self.client.post(self.url, {'action': 'confirm'})
        self.assertEqual(r.context['done']['existing'], 1)
        self.assertEqual(Payslip.objects.get(employee=self.a).id, old.id)
        self.upload()
        self.client.post(self.url, {'action': 'confirm', f'replace_{self.cf_a}': '1'})
        self.assertNotEqual(Payslip.objects.get(employee=self.a).id, old.id)

    def test_wrong_choices_are_refused(self):
        self.upload()
        # stesso dipendente scelto per due cedolini diversi: nessuno dei due viene caricato
        r = self.client.post(self.url, {'action': 'confirm', f'skip_{self.cf_a}': '1',
                                        f'emp_{self.cf_b}': str(self.other.id), f'emp_{self.cf_c}': str(self.other.id)})
        self.assertEqual(r.context['done']['saved'], 0)
        self.assertFalse(Payslip.objects.exists())
        self.other.refresh_from_db()
        self.assertEqual(self.other.fiscal_code, '')
        # un dipendente che ha già un altro codice fiscale non può ricevere il cedolino
        self.upload()
        r = self.client.post(self.url, {'action': 'confirm', f'skip_{self.cf_a}': '1', f'emp_{self.cf_b}': str(self.a.id)})
        self.assertEqual(r.context['done']['saved'], 0)

    def test_mixed_months_and_staff_only(self):
        pdf = lul_pdf([(self.cf_a, 'ROSSI MARIO', 'SETTEMBRE', '2026'), (self.cf_a, 'ROSSI MARIO', 'OTTOBRE', '2026')])
        rows, _ = lul_import.build_rows(lul_import.analyze(pdf))
        self.assertEqual(rows[0]['status'], 'blocked')
        self.client.force_login(self.a.user)
        self.assertEqual(self.client.get(self.url).status_code, 302)
