const LANGUAGE_STORAGE_KEY = "study-web-language";

const I18N_TEXT = {
  en: {
    "nav.courses": "Courses",
    "nav.dashboard": "Dashboard",
    "nav.login": "Log in",
    "nav.logout": "Logout",
    "nav.signup": "Sign up",
    "lesson.previous": "Previous lesson",
    "lesson.next": "Next lesson",
    "lesson.translationLoading": "Translating lesson...",
    "lesson.translationFailed": "Vietnamese translation is temporarily unavailable."
  },
  vi: {
    "nav.courses": "Môn học",
    "nav.dashboard": "Bảng tiến độ",
    "nav.login": "Đăng nhập",
    "nav.logout": "Đăng xuất",
    "nav.signup": "Đăng ký",
    "lesson.previous": "Bài trước",
    "lesson.next": "Bài tiếp theo",
    "lesson.translationLoading": "Đang dịch bài học...",
    "lesson.translationFailed": "Tạm thời chưa tải được bản dịch tiếng Việt."
  }
};

const VIETNAMESE_TEXT_RE = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]/;

function getPreferredLanguage() {
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return stored === "vi" ? "vi" : "en";
}

function hasVietnameseText(value) {
  return VIETNAMESE_TEXT_RE.test(value || "");
}

function setTextPreservingOriginal(element, value) {
  if (!element.dataset.originalText) {
    element.dataset.originalText = element.textContent;
  }
  element.textContent = value || element.dataset.originalText;
}

function applyStaticTranslations(language) {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    setTextPreservingOriginal(element, I18N_TEXT[language]?.[key] || I18N_TEXT.en[key]);
  });
}

function applyLessonTranslations(language) {
  const metadata = document.querySelector(".lesson-translation-meta");
  const lessonContent = document.querySelector(".lesson-content");
  const heading = document.querySelector(".lesson-content h1");
  const summary = document.querySelector(".lesson-content .summary");
  const body = document.querySelector(".lesson-content .content-body");
  const hasManualVietnamese = Boolean(body?.querySelector('.lang-panel[data-lang="vi"]'));

  captureOriginalLessonState(heading, summary, body);
  applyStoredLessonText(language, metadata, heading, summary);

  if (!body || hasManualVietnamese) {
    setTranslationStatus("");
    return;
  }

  if (language === "en" && !lessonNeedsGeneratedEnglish(heading, summary, body)) {
    restoreOriginalLesson(heading, summary, body);
    setTranslationStatus("");
    return;
  }

  applyGeneratedLessonTranslation(lessonContent, heading, summary, body, language);
}

function captureOriginalLessonState(heading, summary, body) {
  if (heading && !heading.dataset.originalText) {
    heading.dataset.originalText = heading.textContent;
  }
  if (summary && !summary.dataset.originalText) {
    summary.dataset.originalText = summary.textContent;
  }
  if (body && !body.__originalHtml) {
    body.__originalHtml = body.innerHTML;
    body.__originalText = body.textContent || "";
  }
}

function applyStoredLessonText(language, metadata, heading, summary) {
  if (heading) {
    heading.textContent = language === "vi" && metadata?.dataset.titleVi
      ? metadata.dataset.titleVi
      : heading.dataset.originalText;
  }
  if (summary) {
    summary.textContent = language === "vi" && metadata?.dataset.summaryVi
      ? metadata.dataset.summaryVi
      : summary.dataset.originalText;
  }
}

function lessonNeedsGeneratedEnglish(heading, summary, body) {
  return hasVietnameseText([
    heading?.dataset.originalText,
    summary?.dataset.originalText,
    body?.__originalText
  ].join(" "));
}

function restoreOriginalLesson(heading, summary, body) {
  if (heading) {
    heading.textContent = heading.dataset.originalText;
  }
  if (summary) {
    summary.textContent = summary.dataset.originalText;
  }
  if (body?.__originalHtml) {
    body.innerHTML = body.__originalHtml;
  }
}

function setTranslationStatus(message) {
  const lessonContent = document.querySelector(".lesson-content");
  if (!lessonContent) {
    return;
  }
  let status = lessonContent.querySelector(".translation-status");
  if (!message) {
    status?.remove();
    return;
  }
  if (!status) {
    status = document.createElement("p");
    status.className = "translation-status";
    const summary = lessonContent.querySelector(".summary");
    if (summary) {
      summary.insertAdjacentElement("afterend", status);
    } else {
      lessonContent.querySelector("h1")?.insertAdjacentElement("afterend", status);
    }
  }
  status.textContent = message;
}

function applyGeneratedPayload(payload, heading, summary, body) {
  if (heading) {
    heading.textContent = payload.title || heading.dataset.originalText;
  }
  if (summary) {
    summary.textContent = payload.summary || summary.dataset.originalText;
  }
  body.innerHTML = payload.content_html || body.__originalHtml;
  setTranslationStatus("");
}

async function applyGeneratedLessonTranslation(lessonContent, heading, summary, body, language) {
  const lessonId = lessonContent?.dataset.lessonId;
  if (!lessonId || body.dataset.translationLoading === language) {
    return;
  }
  if (!body.__translationPayloads) {
    body.__translationPayloads = {};
  }
  if (body.__translationPayloads[language]) {
    applyGeneratedPayload(body.__translationPayloads[language], heading, summary, body);
    return;
  }
  if (language === "en") {
    restoreOriginalLesson(heading, summary, body);
  }
  body.dataset.translationLoading = language;
  setTranslationStatus(I18N_TEXT[language]?.["lesson.translationLoading"] || I18N_TEXT.en["lesson.translationLoading"]);
  try {
    const response = await fetch(`/api/lessons/${lessonId}/translation?lang=${language}`, {
      headers: { Accept: "application/json" }
    });
    if (!response.ok) {
      throw new Error(`Translation failed: ${response.status}`);
    }
    const payload = await response.json();
    body.__translationPayloads[language] = payload;
    if (document.body.dataset.language === language) {
      applyGeneratedPayload(payload, heading, summary, body);
    }
  } catch (error) {
    restoreOriginalLesson(heading, summary, body);
    setTranslationStatus("");
  } finally {
    if (body.dataset.translationLoading === language) {
      body.dataset.translationLoading = "";
    }
  }
}

function applyLanguage(language) {
  document.documentElement.lang = language === "vi" ? "vi" : "en";
  document.body.dataset.language = language;
  localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  applyStaticTranslations(language);
  applyLessonTranslations(language);
  document.querySelectorAll("[data-language-choice]").forEach((button) => {
    const isActive = button.dataset.languageChoice === language;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-language-choice]").forEach((button) => {
    button.addEventListener("click", () => applyLanguage(button.dataset.languageChoice));
  });
  applyLanguage(getPreferredLanguage());
});
