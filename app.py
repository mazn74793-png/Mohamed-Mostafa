from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'teacher_site.db'
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
HOST = '127.0.0.1'
PORT = 5000

SAMPLE_PROFILE = {
    'teacher_name': 'أ/ محمد أحمد',
    'specialization': 'مدرس رياضيات',
    'bio': 'موقع تعليمي لعرض الكورسات، مواعيد الحصص، واستقبال استفسارات الطلاب وأولياء الأمور.',
    'phone': '0100-000-0000',
    'email': 'teacher@example.com',
}

SAMPLE_COURSES = [
    {
        'title': 'تأسيس رياضيات للمرحلة الإعدادية',
        'grade_level': 'الصف الأول والثاني الإعدادي',
        'description': 'شرح الأساسيات بطريقة مبسطة مع تدريبات أسبوعية واختبارات قصيرة.',
        'schedule': 'السبت والثلاثاء - 6:00 مساءً',
    },
    {
        'title': 'جبر وهندسة للثانوية العامة',
        'grade_level': 'الصف الثالث الثانوي',
        'description': 'مراجعة شاملة، حل امتحانات، وخطة متابعة منظمة حتى الامتحان.',
        'schedule': 'الأحد والأربعاء - 8:00 مساءً',
    },
    {
        'title': 'حصص أونلاين مباشرة',
        'grade_level': 'جميع المراحل',
        'description': 'حصص مباشرة عبر الإنترنت مع تسجيل الدرس وإتاحة الواجبات للطلاب.',
        'schedule': 'الاثنين والخميس - 7:00 مساءً',
    },
]

SAMPLE_ANNOUNCEMENTS = [
    'فتح باب الحجز لكورس المراجعة النهائية لشهر أبريل.',
    'يوجد اختبار مجاني لتحديد المستوى للطلاب الجدد.',
    'جميع الحصص الأونلاين يتم إرسال تسجيلها بعد انتهاء الدرس.',
]

MIME_TYPES = {
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            '''
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                teacher_name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                bio TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''
        )

        profile_exists = connection.execute('SELECT 1 FROM profile WHERE id = 1').fetchone()
        if not profile_exists:
            connection.execute(
                '''
                INSERT INTO profile (id, teacher_name, specialization, bio, phone, email)
                VALUES (1, :teacher_name, :specialization, :bio, :phone, :email)
                ''',
                SAMPLE_PROFILE,
            )

        course_count = connection.execute('SELECT COUNT(*) AS count FROM courses').fetchone()['count']
        if course_count == 0:
            connection.executemany(
                '''
                INSERT INTO courses (title, grade_level, description, schedule)
                VALUES (:title, :grade_level, :description, :schedule)
                ''',
                SAMPLE_COURSES,
            )

        announcement_count = connection.execute('SELECT COUNT(*) AS count FROM announcements').fetchone()['count']
        if announcement_count == 0:
            connection.executemany(
                'INSERT INTO announcements (content) VALUES (?)',
                [(announcement,) for announcement in SAMPLE_ANNOUNCEMENTS],
            )


def load_site_content() -> dict[str, Any]:
    with get_connection() as connection:
        profile_row = connection.execute('SELECT * FROM profile WHERE id = 1').fetchone()
        course_rows = connection.execute('SELECT * FROM courses ORDER BY id').fetchall()
        announcement_rows = connection.execute('SELECT * FROM announcements ORDER BY id DESC').fetchall()

    return {
        'profile': dict(profile_row),
        'courses': [dict(course) for course in course_rows],
        'announcements': [dict(announcement) for announcement in announcement_rows],
    }


def save_message(payload: dict[str, str]) -> None:
    with get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO messages (student_name, phone, grade_level, message)
            VALUES (:student_name, :phone, :grade_level, :message)
            ''',
            payload,
        )


def list_messages() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            '''
            SELECT id, student_name, phone, grade_level, message, created_at
            FROM messages
            ORDER BY created_at DESC, id DESC
            '''
        ).fetchall()
    return [dict(row) for row in rows]


class TeacherSiteHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == '/':
            self.serve_file(TEMPLATES_DIR / 'index.html')
            return

        if parsed.path == '/api/site-content':
            self.send_json(load_site_content())
            return

        if parsed.path == '/api/messages':
            self.send_json({'messages': list_messages()})
            return

        if parsed.path.startswith('/static/'):
            requested_path = parsed.path.removeprefix('/static/')
            safe_path = (STATIC_DIR / requested_path).resolve()
            if not str(safe_path).startswith(str(STATIC_DIR.resolve())):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self.serve_file(safe_path)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != '/api/messages':
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get('Content-Length', '0'))
        raw_body = self.rfile.read(content_length)

        try:
            data = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_json({'success': False, 'error': 'صيغة البيانات غير صحيحة.'}, status=HTTPStatus.BAD_REQUEST)
            return

        required_fields = ['student_name', 'phone', 'grade_level', 'message']
        missing_fields = [field for field in required_fields if not str(data.get(field, '')).strip()]

        if missing_fields:
            self.send_json(
                {
                    'success': False,
                    'error': 'يرجى استكمال جميع الحقول المطلوبة.',
                    'missing_fields': missing_fields,
                },
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        payload = {field: str(data[field]).strip() for field in required_fields}
        save_message(payload)
        self.send_json(
            {'success': True, 'message': 'تم إرسال رسالتك بنجاح، وسيتم التواصل معك قريبًا.'},
            status=HTTPStatus.CREATED,
        )

    def serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', MIME_TYPES.get(file_path.suffix, 'application/octet-stream'))
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), TeacherSiteHandler)
    print(f'Server running at http://{HOST}:{PORT}')
    server.serve_forever()


if __name__ == '__main__':
    run()
