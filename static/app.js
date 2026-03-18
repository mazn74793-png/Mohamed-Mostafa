const teacherName = document.getElementById('teacher-name');
const teacherBio = document.getElementById('teacher-bio');
const teacherSpecialization = document.getElementById('teacher-specialization');
const teacherPhone = document.getElementById('teacher-phone');
const teacherEmail = document.getElementById('teacher-email');
const coursesGrid = document.getElementById('courses-grid');
const announcementsList = document.getElementById('announcements-list');
const contactForm = document.getElementById('contact-form');
const formStatus = document.getElementById('form-status');

async function loadSiteContent() {
  const response = await fetch('/api/site-content');
  const data = await response.json();

  teacherName.textContent = data.profile.teacher_name;
  teacherBio.textContent = data.profile.bio;
  teacherSpecialization.textContent = data.profile.specialization;
  teacherPhone.textContent = `الهاتف: ${data.profile.phone}`;
  teacherEmail.textContent = `البريد: ${data.profile.email}`;

  coursesGrid.innerHTML = data.courses
    .map(
      (course) => `
        <article class="card">
          <p class="grade">${course.grade_level}</p>
          <h3>${course.title}</h3>
          <p>${course.description}</p>
          <p class="schedule">🗓️ ${course.schedule}</p>
        </article>
      `
    )
    .join('');

  announcementsList.innerHTML = data.announcements
    .map(
      (announcement) => `
        <article class="announcement">
          <p>${announcement.content}</p>
        </article>
      `
    )
    .join('');
}

contactForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  formStatus.textContent = 'جارٍ إرسال البيانات...';

  const formData = new FormData(contactForm);
  const payload = Object.fromEntries(formData.entries());

  const response = await fetch('/api/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  if (!response.ok) {
    formStatus.textContent = result.error || 'حدث خطأ أثناء إرسال الرسالة.';
    return;
  }

  contactForm.reset();
  formStatus.textContent = result.message;
});

loadSiteContent().catch(() => {
  formStatus.textContent = 'تعذر تحميل بيانات الموقع حاليًا.';
});
