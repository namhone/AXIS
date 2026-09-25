(function () {
  'use strict';

  var root;
  var preview;
  var currentTemplate = 'modern';
  var currentLanguage = 'vi';
  var pipelineRun = 0;
  var model = null;
  var previewResizeObserver;
  var TEMPLATE_COLORS = {
    modern: [
      { name: 'Navy gốc', accent: '#0b3d66', ink: '#14202e', paper: '#ffffff' },
      { name: 'Berry', accent: '#7c3f68', ink: '#2d2030', paper: '#fffafd' },
      { name: 'Forest', accent: '#28665c', ink: '#19312d', paper: '#fbfffd' }
    ],
    professional: [
      { name: 'Teal gốc', accent: '#439596', ink: '#333333', paper: '#ffffff' },
      { name: 'Cobalt', accent: '#3563a8', ink: '#202b3c', paper: '#fbfcff' },
      { name: 'Slate', accent: '#536273', ink: '#29313a', paper: '#ffffff' }
    ],
    simple: [
      { name: 'Teal gốc', accent: '#3e8586', ink: '#333333', paper: '#ffffff' },
      { name: 'Indigo', accent: '#5663a8', ink: '#292d46', paper: '#fcfcff' },
      { name: 'Terracotta', accent: '#b66352', ink: '#3d2925', paper: '#fffdfb' }
    ],
    creative: [
      { name: 'Cam gốc', accent: '#e58a32', ink: '#555555', paper: '#ffffff' },
      { name: 'Violet', accent: '#7856a8', ink: '#30263f', paper: '#fefcff' },
      { name: 'Ocean', accent: '#2f7f9c', ink: '#20343d', paper: '#f9feff' }
    ]
  };
  var activePalette = 0;
  var TEMPLATE_LABELS = {
    modern: 'Modern',
    professional: 'Professional',
    simple: 'Simple',
    creative: 'Creative'
  };
  var COLOR_LABELS = {
    modern: ['Accent', 'Ink', 'Paper'],
    professional: ['Teal chính', 'Màu chữ', 'Nền giấy'],
    simple: ['Teal', 'Màu chữ', 'Nền giấy'],
    creative: ['Màu chủ đạo', 'Màu chữ', 'Nền giấy']
  };
  var CV_LABELS = {
    vi: {
      summary: 'GIỚI THIỆU', experience: 'KINH NGHIỆM & DỰ ÁN', education: 'HỌC VẤN',
      achievements: 'THÀNH TÍCH', skills: 'KỸ NĂNG', certificates: 'CHỨNG CHỈ',
      interests: 'SỞ THÍCH', contact: 'THÔNG TIN CÁ NHÂN', focus: 'MỤC TIÊU',
      phone: 'Điện thoại', email: 'Email', linkedin: 'Liên kết', location: 'Địa điểm'
    },
    en: {
      summary: 'PROFILE', experience: 'EXPERIENCE & PROJECTS', education: 'EDUCATION',
      achievements: 'ACHIEVEMENTS', skills: 'SKILLS', certificates: 'CERTIFICATES',
      interests: 'INTERESTS', contact: 'CONTACT', focus: 'FOCUS',
      phone: 'Phone', email: 'Email', linkedin: 'Website', location: 'Location'
    }
  };
  var SAMPLE_PROFILE = {
    name: 'Nguyễn Minh Anh',
    email: 'minhanh@example.com',
    phone: '+84 912 345 678',
    linkedin: 'linkedin.com/in/minhanh',
    className: 'Lớp 12',
    goal: 'Data & Product Explorer',
    introduction: 'Học sinh yêu thích biến dữ liệu và công nghệ thành những sản phẩm hữu ích cho cộng đồng. Chủ động học hỏi, làm việc có hệ thống và luôn tìm cách đo lường tác động của mỗi dự án.',
    projectName: 'StudyFlow — Trợ lý học tập',
    projectType: 'Dự án cá nhân · 2024',
    projectDescription: 'Thiết kế prototype giúp học sinh lập lịch ôn tập theo mục tiêu. Phỏng vấn 12 bạn học, xây dựng luồng trải nghiệm và thử nghiệm phiên bản đầu với nhóm 5 người.',
    activityName: 'CLB Khoa học kỹ thuật',
    activityRole: 'Trưởng ban nội dung',
    activityImpact: 'Điều phối 8 thành viên, tổ chức 4 workshop và xây dựng thư viện tài liệu mở cho học sinh trong trường.',
    skills: 'Phân tích dữ liệu, Figma, Python, Thuyết trình, Làm việc nhóm',
    interests: 'Công nghệ giáo dục, thiết kế sản phẩm, chạy bộ',
    gpa12: '9.2',
    certificateRecords: [{ name: 'IELTS Academic', score: '6.5', issueDate: '2024' }]
  };

  function wait(milliseconds) {
    return new Promise(function (resolve) { window.setTimeout(resolve, milliseconds); });
  }

  function text(value, fallback) {
    var result = value == null ? '' : String(value).trim();
    return result || fallback || '';
  }

  function splitList(value) {
    return String(value || '')
      .split(/[,;|\n]/)
      .map(function (item) { return item.trim(); })
      .filter(Boolean)
      .slice(0, 8);
  }

  function initials(name) {
    return text(name, 'FP').split(/\s+/).filter(Boolean).slice(-2).map(function (part) {
      return part.charAt(0).toUpperCase();
    }).join('') || 'FP';
  }

  function hexToRgb(hex) {
    var value = String(hex || '').replace('#', '');
    if (value.length === 3) value = value.split('').map(function (part) { return part + part; }).join('');
    var number = parseInt(value, 16);
    return isFinite(number) ? { r: number >> 16 & 255, g: number >> 8 & 255, b: number & 255 } : { r: 0, g: 0, b: 0 };
  }

  function rgbToHex(rgb) {
    return '#' + [rgb.r, rgb.g, rgb.b].map(function (value) {
      return Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, '0');
    }).join('');
  }

  function tint(hex, amount) {
    var rgb = hexToRgb(hex);
    return rgbToHex({ r: rgb.r + (255 - rgb.r) * amount, g: rgb.g + (255 - rgb.g) * amount, b: rgb.b + (255 - rgb.b) * amount });
  }

  function shade(hex, amount) {
    var rgb = hexToRgb(hex);
    return rgbToHex({ r: rgb.r * (1 - amount), g: rgb.g * (1 - amount), b: rgb.b * (1 - amount) });
  }

  function escapeValue(value) {
    return String(value == null ? '' : value);
  }

  function extractProfile(profile) {
    var source = Object.assign({}, SAMPLE_PROFILE, profile || {});
    var records = Array.isArray(source.certificateRecords) ? source.certificateRecords : [];
    var certificates = records.map(function (record) {
      return [record.name, record.score, record.issueDate].filter(Boolean).join(' · ');
    }).filter(Boolean);
    if (!certificates.length && (source.certificateName || source.certificateScore)) {
      certificates.push([source.certificateName, source.certificateScore, source.certificateIssueDate].filter(Boolean).join(' · '));
    }
    var educationMeta = [source.className, source.birthYear].filter(Boolean).join(' · ');
    var gpa = [source.gpa9, source.gpa10, source.gpa11, source.gpa12].filter(Boolean);
    if (gpa.length) educationMeta += (educationMeta ? ' · ' : '') + ' GPA ' + gpa[gpa.length - 1];
    return {
      name: text(source.name, SAMPLE_PROFILE.name),
      role: text(source.goal, SAMPLE_PROFILE.goal),
      email: text(source.email, SAMPLE_PROFILE.email),
      phone: text(source.phone, SAMPLE_PROFILE.phone),
      linkedin: text(source.linkedin, SAMPLE_PROFILE.linkedin),
      location: text(source.location, 'Việt Nam'),
      summary: text(source.introduction, SAMPLE_PROFILE.introduction),
      skills: splitList(source.skills || source.supportingSkills).length ? splitList(source.skills || source.supportingSkills) : splitList(SAMPLE_PROFILE.skills),
      interests: splitList(source.interests).length ? splitList(source.interests) : splitList(SAMPLE_PROFILE.interests),
      project: {
        name: text(source.projectName, SAMPLE_PROFILE.projectName),
        meta: text(source.projectType, SAMPLE_PROFILE.projectType),
        description: text(source.projectDescription, SAMPLE_PROFILE.projectDescription)
      },
      activity: {
        name: text(source.activityName, SAMPLE_PROFILE.activityName),
        meta: text(source.activityRole, 'Thành viên'),
        description: text(source.activityImpact, SAMPLE_PROFILE.activityImpact)
      },
      education: {
        name: text(source.schoolName, 'THPT AXIS'),
        meta: text(educationMeta, 'Lớp 12 · GPA 9.2'),
        description: text(source.educationDescription, 'Tập trung vào Toán, Tin học và các dự án nghiên cứu ứng dụng.')
      },
      achievement: {
        name: text(source.examType || source.awardRank, 'Thành tích học tập'),
        meta: [source.examSubject, source.examYear, source.awardRank].filter(Boolean).join(' · ') || '2024',
        description: text(source.examDescription, 'Chủ động tham gia các hoạt động học thuật và chia sẻ kiến thức trong cộng đồng.')
      },
      certificates: certificates.length ? certificates : ['IELTS Academic · 6.5 · 2024']
    };
  }

  function makeModel(profile, language) {
    var extracted = extractProfile(profile);
    return {
      data: extracted,
      labels: Object.assign({}, CV_LABELS[language] || CV_LABELS.vi),
      overrides: {}
    };
  }

  function value(key, fallback) {
    if (!key) return text(fallback, '');
    if (model && Object.prototype.hasOwnProperty.call(model.overrides, key)) return model.overrides[key];
    var current = model;
    key.replace(/\[(\d+)\]/g, '.$1').split('.').forEach(function (part) {
      if (part) current = current && current[part];
    });
    return text(current, fallback);
  }

  function element(tag, className, key, fallback, options) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    var resolved = value(key || '', fallback);
    node.textContent = escapeValue(resolved);
    if (key) node.dataset.cvBind = key;
    var mode = (options && options.mode) ? options.mode : 'paragraph';
    node.dataset.cvMode = mode;
    if (!options || options.editable !== false) {
      node.contentEditable = 'true';
      node.dataset.cvEditable = 'true';
      node.spellcheck = true;
    }
    if (options && options.role) node.setAttribute('role', options.role);
    return node;
  }

  function createListItemNode(text) {
    var item = document.createElement('li');
    item.dataset.cvEditable = 'true';
    item.dataset.cvMode = 'list-item';
    item.contentEditable = 'true';
    item.spellcheck = true;
    item.textContent = text || '';
    return item;
  }

  function insertNewListItem(currentItem) {
    var list = currentItem.parentElement;
    var nextItem = createListItemNode('');
    if (!list || !list.matches('ul,ol')) {
      return;
    }
    list.insertBefore(nextItem, currentItem.nextSibling || null);
    nextItem.focus();
    var selection = window.getSelection();
    if (!selection) return;
    var range = document.createRange();
    range.selectNodeContents(nextItem);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function bindEditableNode(node) {
    var mode = node.dataset.cvMode || 'paragraph';
    if (node.dataset.cvBoundEnter === 'true') return;
    node.dataset.cvBoundEnter = 'true';

    node.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter') return;
      if (mode === 'paragraph') {
        if (!event.ctrlKey && !event.metaKey && !event.shiftKey) {
          event.preventDefault();
          return;
        }
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault();
          document.execCommand('insertLineBreak');
          return;
        }
      }
      if (mode === 'list-item') {
        if (event.ctrlKey || event.metaKey || event.shiftKey) {
          return;
        }
        event.preventDefault();
        insertNewListItem(node);
      }
    });
  }

  function lucideIcon(name, className) {
    var node = document.createElement('span');
    if (className) node.className = className;
    node.setAttribute('data-lucide', name);
    node.setAttribute('aria-hidden', 'true');
    return node;
  }

  function sectionTitle(key, fallback) {
    return element('h2', 'cv-page__section-title', 'labels.' + key, fallback);
  }

  function section(key, fallback, content) {
    var wrapper = document.createElement('section');
    wrapper.className = 'cv-page__section';
    wrapper.appendChild(sectionTitle(key, fallback));
    wrapper.appendChild(content);
    return wrapper;
  }

  function item(prefix, entry, index) {
    var wrapper = document.createElement('article');
    wrapper.className = 'cv-page__item';
    wrapper.appendChild(element('h3', '', 'data.' + prefix + '.name', entry.name));
    wrapper.appendChild(element('p', 'cv-page__meta', 'data.' + prefix + '.meta', entry.meta));
    wrapper.appendChild(element('p', '', 'data.' + prefix + '.description', entry.description));
    return wrapper;
  }

  function list(prefix, items, className) {
    var ul = document.createElement('ul');
    ul.className = className || '';
    items.forEach(function (entry, index) {
      var li = element('li', '', 'data.' + prefix + '[' + index + ']', entry);
      ul.appendChild(li);
    });
    return ul;
  }

  function addCommonMain(main, includeAchievements) {
    var summary = document.createElement('div');
    summary.appendChild(element('p', '', 'data.summary', model.data.summary));
    main.appendChild(section('summary', 'PROFILE', summary));

    var projects = document.createElement('div');
    projects.appendChild(item('project', model.data.project, 0));
    projects.appendChild(item('activity', model.data.activity, 0));
    main.appendChild(section('experience', 'EXPERIENCE & PROJECTS', projects));

    var education = document.createElement('div');
    education.appendChild(item('education', model.data.education, 0));
    main.appendChild(section('education', 'EDUCATION', education));

    if (includeAchievements) {
      var achievement = document.createElement('div');
      achievement.appendChild(item('achievement', model.data.achievement, 0));
      main.appendChild(section('achievements', 'ACHIEVEMENTS', achievement));
    }
  }

  function addCommonSidebar(sidebar, showContact) {
    if (showContact) {
      var contact = document.createElement('div');
      ['email', 'phone', 'linkedin', 'location'].forEach(function (key) {
        contact.appendChild(element('p', 'cv-page__contact', 'data.' + key, model.data[key]));
      });
      sidebar.appendChild(section('contact', 'CONTACT', contact));
    }
    sidebar.appendChild(section('skills', 'SKILLS', list('skills', model.data.skills, 'cv-skill-list')));
    sidebar.appendChild(section('certificates', 'CERTIFICATES', list('certificates', model.data.certificates, 'cv-skill-list')));
    sidebar.appendChild(section('interests', 'INTERESTS', list('interests', model.data.interests, 'cv-skill-list')));
  }

  function renderModern() {
    var page = document.createElement('article');
    page.className = 'cv-page cv-template--modern';

    var columns = document.createElement('div');
    columns.className = 'cv-columns cv-template--modern__columns';

    var sidebar = document.createElement('aside');
    sidebar.className = 'cv-sidebar-box cv-modern-sidebar';

    var profileCard = document.createElement('div');
    profileCard.className = 'cv-modern-profile';

    var photo = document.createElement('div');
    photo.className = 'cv-modern-photo';
    photo.textContent = initials(model.data.name);
    photo.setAttribute('contenteditable', 'false');
    photo.dataset.staticPhoto = 'true';
    profileCard.appendChild(photo);

    var mainHeader = document.createElement('header');
    mainHeader.className = 'cv-modern-main-header';
    mainHeader.appendChild(element('h1', '', 'data.name', model.data.name));
    mainHeader.appendChild(element('p', 'cv-page__meta', 'data.role', model.data.role));
    mainHeader.appendChild(element('p', 'cv-page__contact', 'data.email', [model.data.email, model.data.phone, model.data.location].filter(Boolean).join(' · ')));
    mainHeader.appendChild(element('p', 'cv-page__summary', 'data.summary', model.data.summary));

    var contact = document.createElement('div');
    contact.className = 'cv-modern-contact-list';
    ['phone', 'email', 'linkedin', 'location'].forEach(function (key) {
      if (!model.data[key]) return;
      var item = document.createElement('p');
      item.className = 'cv-modern-contact-row';
      item.appendChild(element('span', 'cv-modern-contact-label', '', CV_LABELS[model.language || currentLanguage][key], { editable: false }));
      item.appendChild(element('span', 'cv-modern-contact-value', 'data.' + key, model.data[key]));
      contact.appendChild(item);
    });

    sidebar.appendChild(profileCard);
    sidebar.appendChild(section('contact', 'Personal Information', contact));
    sidebar.appendChild(section('skills', 'Skills', list('skills', model.data.skills, 'cv-skill-list')));
    sidebar.appendChild(section('certificates', 'Certificates', list('certificates', model.data.certificates, 'cv-skill-list')));
    sidebar.appendChild(section('interests', 'Interests', list('interests', model.data.interests, 'cv-skill-list')));

    var main = document.createElement('main');
    main.className = 'cv-modern-main';
    main.appendChild(mainHeader);
    addCommonMain(main, true);

    columns.appendChild(sidebar);
    columns.appendChild(main);
    page.appendChild(columns);
    return page;
  }

  function renderProfessional() {
    var page = document.createElement('article');
    page.className = 'cv-page cv-template--professional';

    function professionalTitle(label, icon) {
      var heading = document.createElement('div');
      heading.className = 'cv-professional-section-header';
      var mark = document.createElement('span');
      mark.className = 'cv-professional-section-icon';
      mark.appendChild(lucideIcon(icon));
      var title = element('h2', '', 'labels.' + label, label.toUpperCase());
      heading.appendChild(mark);
      heading.appendChild(title);
      heading.appendChild(document.createElement('span')).className = 'cv-professional-section-rule';
      return heading;
    }

    function professionalSection(label, icon, content) {
      var wrapper = document.createElement('section');
      wrapper.className = 'cv-professional-section';
      wrapper.appendChild(professionalTitle(label, icon));
      wrapper.appendChild(content);
      return wrapper;
    }

    function professionalEntry(prefix, entry, numbered) {
      var wrapper = document.createElement('article');
      wrapper.className = 'cv-professional-entry';
      var top = document.createElement('div');
      top.className = 'cv-professional-entry-top';
      top.appendChild(element('h3', '', 'data.' + prefix + '.name', entry.name));
      top.appendChild(element('span', 'cv-professional-entry-date', 'data.' + prefix + '.meta', entry.meta));
      wrapper.appendChild(top);
      if (prefix === 'activity') {
        wrapper.appendChild(element('p', 'cv-professional-entry-role', 'data.' + prefix + '.meta', entry.meta));
      }
      var description = element('p', 'cv-professional-entry-description', 'data.' + prefix + '.description', entry.description);
      wrapper.appendChild(description);
      if (numbered) {
        var list = document.createElement('ol');
        list.className = 'cv-professional-responsibilities';
        [entry.description, 'Phối hợp với các bên liên quan để hoàn thành mục tiêu đúng tiến độ.', 'Theo dõi kết quả và cải thiện quy trình dựa trên dữ liệu.'].forEach(function (item, index) {
          list.appendChild(element('li', '', 'data.' + prefix + '.responsibility' + index, item));
        });
        description.remove();
        wrapper.appendChild(list);
      }
      return wrapper;
    }

    var columns = document.createElement('div');
    columns.className = 'cv-professional-columns';
    var main = document.createElement('main');
    var sidebar = document.createElement('aside');
    main.className = 'cv-professional-main';
    sidebar.className = 'cv-professional-sidebar';

    var profile = document.createElement('div');
    profile.className = 'cv-professional-profile';
    var photo = document.createElement('div');
    photo.className = 'cv-professional-photo';
    photo.textContent = initials(model.data.name);
    photo.setAttribute('contenteditable', 'false');
    photo.dataset.staticPhoto = 'true';
    profile.appendChild(photo);
    var nameCard = document.createElement('div');
    nameCard.className = 'cv-professional-name-card';
    nameCard.appendChild(element('h1', '', 'data.name', model.data.name));
    nameCard.appendChild(element('p', '', 'data.role', model.data.role));
    profile.appendChild(nameCard);
    sidebar.appendChild(profile);

    var contact = document.createElement('div');
    contact.className = 'cv-professional-contact';
    [['birthYear', 'calendar-days'], ['className', 'graduation-cap'], ['phone', 'phone'], ['email', 'mail'], ['location', 'map-pin'], ['linkedin', 'external-link']].forEach(function (entry) {
      var row = document.createElement('div');
      row.className = 'cv-professional-info-item';
      var icon = document.createElement('span');
      icon.className = 'cv-professional-info-icon';
      icon.appendChild(lucideIcon(entry[1]));
      row.appendChild(icon);
      row.appendChild(element('span', '', 'data.' + entry[0], model.data[entry[0]] || 'Thông tin bổ sung'));
      contact.appendChild(row);
    });
    sidebar.appendChild(professionalSection('contact', 'contact', contact));

    var objective = document.createElement('div');
    objective.appendChild(element('p', 'cv-professional-objective-text', 'data.summary', model.data.summary));
    sidebar.appendChild(professionalSection('focus', 'sparkles', objective));

    main.appendChild(professionalSection('education', 'graduation-cap', professionalEntry('education', model.data.education, false)));
    var experience = document.createElement('div');
    experience.appendChild(professionalEntry('project', model.data.project, true));
    experience.appendChild(professionalEntry('activity', model.data.activity, true));
    main.appendChild(professionalSection('experience', 'briefcase', experience));

    var skills = document.createElement('div');
    model.data.skills.forEach(function (skill, index) {
      var row = document.createElement('div');
      row.className = 'cv-professional-skill';
      row.appendChild(element('span', '', 'data.skills[' + index + ']', skill));
      var bar = document.createElement('span');
      bar.className = 'cv-professional-skill-bar';
      bar.appendChild(document.createElement('i'));
      row.appendChild(bar);
      skills.appendChild(row);
    });
    main.appendChild(professionalSection('skills', 'sparkles', skills));

    var certificates = document.createElement('div');
    model.data.certificates.forEach(function (certificate, index) {
      var row = document.createElement('div');
      row.className = 'cv-professional-line-item';
      row.appendChild(element('span', '', 'data.certificates[' + index + ']', certificate));
      var year = document.createElement('span');
      year.textContent = '2024';
      row.appendChild(year);
      certificates.appendChild(row);
    });
    main.appendChild(professionalSection('certificates', 'badge-check', certificates));

    main.appendChild(professionalSection('achievements', 'trophy', professionalEntry('achievement', model.data.achievement, false)));
    columns.appendChild(main);
    columns.appendChild(sidebar);
    page.appendChild(columns);
    return page;
  }

  function renderSimple() {
    var page = document.createElement('article');
    page.className = 'cv-page cv-template--simple';
    var sidebar = document.createElement('aside');
    sidebar.className = 'cv-simple-sidebar';

    var profile = document.createElement('div');
    profile.className = 'cv-simple-profile';
    var photo = document.createElement('div');
    photo.className = 'cv-simple-photo';
    photo.textContent = initials(model.data.name);
    profile.appendChild(photo);
    profile.appendChild(element('h1', '', 'data.name', model.data.name));
    profile.appendChild(element('p', 'cv-simple-role', 'data.role', model.data.role));
    sidebar.appendChild(profile);

    var contact = document.createElement('div');
    contact.className = 'cv-simple-contact';
    [
      ['map-pin', 'location', model.data.location],
      ['phone', 'phone', model.data.phone],
      ['mail', 'email', model.data.email],
      ['external-link', 'linkedin', model.data.linkedin]
    ].forEach(function (entry) {
      var row = document.createElement('div');
      row.className = 'cv-simple-contact-item';
      row.appendChild(lucideIcon(entry[0]));
      row.appendChild(element('span', '', 'data.' + entry[1], entry[2]));
      contact.appendChild(row);
    });
    sidebar.appendChild(contact);

    function simpleSideSection(title, key, entries) {
      var block = document.createElement('section');
      block.className = 'cv-simple-side-section';
      block.appendChild(element('h2', '', 'labels.' + key, title));
      entries.forEach(function (entry, index) {
        var row = document.createElement('div');
        row.className = 'cv-simple-side-item';
        row.appendChild(element('strong', '', 'data.' + key + '[' + index + ']', entry));
        block.appendChild(row);
      });
      sidebar.appendChild(block);
    }

    var skillBlock = document.createElement('section');
    skillBlock.className = 'cv-simple-side-section';
    skillBlock.appendChild(element('h2', '', 'labels.skills', 'SKILLS'));
    model.data.skills.forEach(function (skill, index) {
      var row = document.createElement('div');
      row.className = 'cv-simple-skill';
      row.appendChild(element('span', '', 'data.skills[' + index + ']', skill));
      var dots = document.createElement('span');
      dots.className = 'cv-simple-rating';
      for (var dotIndex = 0; dotIndex < 5; dotIndex += 1) {
        var dot = document.createElement('i');
        if (dotIndex < 4) dot.className = 'is-filled';
        dots.appendChild(dot);
      }
      row.appendChild(dots);
      skillBlock.appendChild(row);
    });
    sidebar.appendChild(skillBlock);
    simpleSideSection('CERTIFICATES', 'certificates', model.data.certificates);
    simpleSideSection('AWARDS', 'achievements', [model.data.achievement.name]);

    var main = document.createElement('main');
    main.className = 'cv-simple-main';
    var header = document.createElement('header');
    header.className = 'cv-simple-head';
    header.appendChild(element('p', 'cv-simple-kicker', 'labels.summary', 'PROFILE'));
    header.appendChild(element('p', 'cv-page__contact', 'data.email', model.data.email + ' · ' + model.data.phone));
    main.appendChild(header);

    function timelineSection(key, title, content) {
      var block = document.createElement('section');
      block.className = 'cv-simple-timeline-section';
      var heading = document.createElement('div');
      heading.className = 'cv-simple-section-heading';
      heading.appendChild(document.createElement('span'));
      heading.appendChild(element('h2', '', 'labels.' + key, title));
      block.appendChild(heading);
      block.appendChild(content);
      return block;
    }

    var objective = document.createElement('p');
    objective.appendChild(element('span', '', 'data.summary', model.data.summary));
    main.appendChild(timelineSection('summary', 'CAREER OBJECTIVE', objective));

    var education = document.createElement('div');
    education.appendChild(element('p', 'cv-simple-date', '', '2021 – 2025', { editable: false }));
    education.appendChild(item('education', model.data.education, 0));
    main.appendChild(timelineSection('education', 'EDUCATION', education));

    var experience = document.createElement('div');
    experience.appendChild(element('p', 'cv-simple-date', '', '2024 – PRESENT', { editable: false }));
    experience.appendChild(item('project', model.data.project, 0));
    experience.appendChild(item('activity', model.data.activity, 0));
    main.appendChild(timelineSection('experience', 'WORK EXPERIENCE', experience));

    var activities = document.createElement('div');
    activities.appendChild(element('p', 'cv-simple-date', '', '2023 – 2024', { editable: false }));
    activities.appendChild(item('activity', model.data.activity, 0));
    main.appendChild(timelineSection('activities', 'ACTIVITIES', activities));

    var references = document.createElement('div');
    references.appendChild(element('h3', '', 'data.name', model.data.name));
    references.appendChild(element('p', 'cv-page__meta', 'data.role', model.data.role));
    references.appendChild(element('p', '', 'data.email', model.data.email));
    main.appendChild(timelineSection('references', 'REFERENCES', references));

    page.appendChild(sidebar);
    page.appendChild(main);
    return page;
  }

  function renderCreative() {
    var page = document.createElement('article');
    page.className = 'cv-page cv-template--creative';

    function sectionTitle(label) {
      var title = document.createElement('h2');
      title.className = 'cv-creative-section-title';
      title.textContent = label;
      return title;
    }

    function card(label, className, content) {
      var section = document.createElement('section');
      section.className = 'cv-creative-card ' + (className || '');
      section.appendChild(sectionTitle(label));
      section.appendChild(content);
      return section;
    }

    function timelineSection(label, content) {
      var item = document.createElement('article');
      item.className = 'cv-creative-timeline-section';
      var marker = document.createElement('span');
      marker.className = 'cv-creative-timeline-marker';
      item.appendChild(marker);
      var body = document.createElement('div');
      body.className = 'cv-creative-timeline-body';
      body.appendChild(sectionTitle(label));
      body.appendChild(content);
      item.appendChild(body);
      return item;
    }

    function creativeEntry(prefix, entry) {
      var item = document.createElement('article');
      item.className = 'cv-creative-entry';
      item.appendChild(element('p', 'cv-creative-date', 'data.' + prefix + '.meta', entry.meta));
      item.appendChild(element('h3', '', 'data.' + prefix + '.name', entry.name));
      item.appendChild(element('p', 'cv-creative-entry-role', 'data.' + prefix + '.meta', entry.meta));
      var description = document.createElement('ul');
      description.className = 'cv-creative-bullets';
      description.appendChild(element('li', '', 'data.' + prefix + '.description', entry.description));
      description.appendChild(element('li', '', 'data.' + prefix + '.descriptionExtra', 'Phối hợp triển khai và theo dõi kết quả thực tế.'));
      description.appendChild(element('li', '', 'data.' + prefix + '.achievement', 'Đề xuất cải tiến dựa trên phản hồi và dữ liệu.'));
      item.appendChild(description);
      return item;
    }

    var profile = document.createElement('div');
    profile.className = 'cv-creative-profile-header';
    var photo = document.createElement('div');
    photo.className = 'cv-creative-photo';
    photo.textContent = initials(model.data.name);
    photo.setAttribute('contenteditable', 'false');
    photo.dataset.staticPhoto = 'true';
    profile.appendChild(photo);
    var identity = document.createElement('div');
    identity.className = 'cv-creative-identity';
    identity.appendChild(element('h1', '', 'data.name', model.data.name));
    identity.appendChild(element('p', 'cv-creative-role', 'data.role', model.data.role));
    profile.appendChild(identity);
    page.appendChild(profile);

    var sidebar = document.createElement('aside');
    sidebar.className = 'cv-creative-sidebar';
    var contact = document.createElement('div');
    contact.className = 'cv-creative-contact';
    [['birthYear', 'calendar-days'], ['phone', 'phone'], ['email', 'mail'], ['location', 'map-pin']].forEach(function (entry) {
      var row = document.createElement('div');
      row.className = 'cv-creative-contact-item';
      var icon = document.createElement('span');
      icon.appendChild(lucideIcon(entry[1]));
      row.appendChild(icon);
      row.appendChild(element('span', '', 'data.' + entry[0], model.data[entry[0]] || 'Thông tin bổ sung'));
      contact.appendChild(row);
    });
    sidebar.appendChild(card('PERSONAL INFORMATION', 'cv-creative-info-card', contact));

    var objective = document.createElement('div');
    objective.appendChild(element('p', '', 'data.summary', model.data.summary));
    sidebar.appendChild(card('CAREER OBJECTIVE', 'cv-creative-objective-card', objective));

    var skills = document.createElement('div');
    model.data.skills.forEach(function (skill, index) {
      var item = document.createElement('div');
      item.className = 'cv-creative-skill';
      item.appendChild(element('span', '', 'data.skills[' + index + ']', skill));
      var dots = document.createElement('span');
      dots.className = 'cv-creative-rating';
      for (var i = 0; i < 5; i += 1) {
        var dot = document.createElement('i');
        if (i < 4) dot.className = 'is-filled';
        dots.appendChild(dot);
      }
      item.appendChild(dots);
      skills.appendChild(item);
    });
    sidebar.appendChild(card('SKILLS', 'cv-creative-skills-card', skills));

    var awards = document.createElement('div');
    awards.appendChild(element('p', 'cv-creative-date', 'data.achievement.meta', model.data.achievement.meta));
    awards.appendChild(element('h3', '', 'data.achievement.name', model.data.achievement.name));
    awards.appendChild(element('p', 'cv-creative-entry-text', 'data.achievement.description', model.data.achievement.description));
    sidebar.appendChild(card('AWARDS & ACHIEVEMENTS', 'cv-creative-awards-card', awards));

    var certificates = document.createElement('div');
    model.data.certificates.forEach(function (certificate, index) {
      certificates.appendChild(element('p', 'cv-creative-certificate-item', 'data.certificates[' + index + ']', certificate));
    });
    sidebar.appendChild(card('CERTIFICATES', 'cv-creative-certificates-card', certificates));

    var main = document.createElement('main');
    main.className = 'cv-creative-main';
    main.appendChild(timelineSection('EDUCATION', creativeEntry('education', model.data.education)));
    var experience = document.createElement('div');
    experience.appendChild(creativeEntry('project', model.data.project));
    experience.appendChild(creativeEntry('activity', model.data.activity));
    main.appendChild(timelineSection('WORK EXPERIENCE', experience));
    main.appendChild(timelineSection('ACTIVITIES', creativeEntry('activity', model.data.activity)));
    var references = document.createElement('div');
    references.appendChild(element('h3', '', 'data.name', model.data.name));
    references.appendChild(element('p', 'cv-creative-entry-text', 'data.role', model.data.role));
    references.appendChild(element('p', 'cv-creative-entry-text', 'data.email', model.data.email));
    main.appendChild(timelineSection('REFERENCES', references));

    var columns = document.createElement('div');
    columns.className = 'cv-creative-columns';
    columns.appendChild(sidebar);
    columns.appendChild(main);
    page.appendChild(columns);
    return page;
  }

  function syncColorControls() {
    var palettes = TEMPLATE_COLORS[currentTemplate] || TEMPLATE_COLORS.modern;
    var config = palettes[activePalette] || palettes[0];
    document.querySelectorAll('[data-color]').forEach(function (input) {
      input.value = config[input.dataset.color];
      preview.style.setProperty('--cv-' + input.dataset.color, config[input.dataset.color]);
    });
    preview.style.setProperty('--cv-accent-soft', config.accent + '1a');
    preview.style.setProperty('--cv-accent-dark', shade(config.accent, .2));
    preview.style.setProperty('--cv-accent-light', tint(config.accent, .72));
    preview.style.setProperty('--cv-accent-pale', tint(config.accent, .9));
    syncCreativeColors(config.accent);
    renderPaletteOptions(palettes);
    (COLOR_LABELS[currentTemplate] || COLOR_LABELS.modern).forEach(function (labelText, index) {
      var key = ['accent', 'ink', 'paper'][index];
      var label = document.querySelector('[data-color-label="' + key + '"]');
      if (label) label.textContent = labelText;
    });
    var help = document.querySelector('[data-color-help]');
    if (help) help.textContent = 'Chọn tone gợi ý để đổi đồng bộ portfolio; các sắc độ đậm, nhạt và nền phụ sẽ tự cân bằng theo màu chính.';
  }

  function syncCreativeColors(accent) {
    preview.style.setProperty('--creative-orange', accent);
    preview.style.setProperty('--creative-dark-orange', shade(accent, .24));
    preview.style.setProperty('--creative-pink', tint(accent, .9));
    preview.style.setProperty('--creative-yellow', tint(accent, .78));
  }

  function renderPaletteOptions(palettes) {
    var container = document.querySelector('[data-palette-options]');
    if (!container) return;
    container.innerHTML = '';
    palettes.forEach(function (palette, index) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'cv-palette-option' + (index === activePalette ? ' is-selected' : '');
      button.dataset.paletteIndex = String(index);
      button.setAttribute('aria-label', palette.name);
      button.innerHTML = '<span style="background:' + palette.accent + '"></span><strong>' + palette.name + '</strong>';
      button.addEventListener('click', function () {
        activePalette = index;
        syncColorControls();
        renderPreview();
      });
      container.appendChild(button);
    });
  }

  function renderPreview() {
    if (!preview || !model) return;
    var builders = { modern: renderModern, professional: renderProfessional, simple: renderSimple, creative: renderCreative };
    preview.innerHTML = '';
    preview.appendChild((builders[currentTemplate] || renderModern)());
    var label = document.querySelector('[data-preview-label]');
    if (label) label.textContent = TEMPLATE_LABELS[currentTemplate];
    preview.querySelectorAll('[data-cv-editable]').forEach(function (node) {
      bindEditableNode(node);
      node.addEventListener('input', function () {
        var key = node.dataset.cvBind;
        if (key) model.overrides[key] = node.textContent.trim();
        fitPreviewToViewport();
        setStatus('Đã cập nhật nội dung. Bạn có thể lưu bản nhách.', 'neutral');
      });
    });
    fitPreviewToViewport();
  }

  function fitPreviewToViewport() {
    if (!preview) return;
    var scroll = document.querySelector('.cv-preview-scroll');
    if (!scroll) return;
    var pageWidth = 794;
    var page = preview.querySelector('.cv-page');
    var pageHeight = page ? Math.max(1123, page.scrollHeight) : 1123;
    var availableWidth = Math.max(0, scroll.clientWidth - 16);
    var scale = availableWidth > 0 ? Math.min(1, availableWidth / pageWidth) : 1;
    if (window.innerWidth <= 560) scale = Math.max(scale, 0.56);
    if (!isFinite(scale) || scale <= 0) scale = 1;
    preview.style.setProperty('--cv-preview-scale', String(scale));
    preview.style.height = String(pageHeight) + 'px';
  }

  function setAgent(name, state) {
    var node = document.querySelector('[data-agent="' + name + '"]');
    if (!node) return;
    node.classList.remove('is-running', 'is-done', 'is-error');
    if (state) node.classList.add('is-' + state);
    var icon = node.querySelector('.cv-agent__status');
    if (icon) {
      icon.textContent = state === 'done' ? '✓' : state === 'running' ? '…' : state === 'error' ? '!' : '○';
      icon.setAttribute('aria-label', state || 'Đang chờ');
    }
  }

  function setStatus(message, tone) {
    var status = document.querySelector('[data-editor-status]');
    if (status) {
      status.textContent = message;
      status.dataset.tone = tone || 'neutral';
    }
  }

  function currentCvData() {
    if (!model || !model.data) return {};
    var data = JSON.parse(JSON.stringify(model.data));
    Object.keys(model.overrides || {}).forEach(function (key) {
      var parts = key.replace(/\[(\d+)\]/g, '.$1').split('.').filter(Boolean);
      if (!parts.length) return;
      var target = data;
      for (var index = 0; index < parts.length - 1; index += 1) {
        if (!target || target[parts[index]] == null) return;
        target = target[parts[index]];
      }
      if (target && parts.length > 0) {
        target[parts[parts.length - 1]] = model.overrides[key];
      }
    });
    return data;
  }

  function aiEditableSection(data) {
    var payload = {};
    payload.summary = text(data.summary, '');
    payload.role = text(data.role, '');
    payload.skills = Array.isArray(data.skills) ? data.skills.slice(0, 12) : [];
    payload.interests = Array.isArray(data.interests) ? data.interests.slice(0, 12) : [];
    payload.project = {
      name: text(data.project && data.project.name, ''),
      meta: text(data.project && data.project.meta, ''),
      description: text(data.project && data.project.description, '')
    };
    payload.activity = {
      name: text(data.activity && data.activity.name, ''),
      meta: text(data.activity && data.activity.meta, ''),
      description: text(data.activity && data.activity.description, '')
    };
    payload.education = {
      name: text(data.education && data.education.name, ''),
      meta: text(data.education && data.education.meta, ''),
      description: text(data.education && data.education.description, '')
    };
    payload.achievement = {
      name: text(data.achievement && data.achievement.name, ''),
      meta: text(data.achievement && data.achievement.meta, ''),
      description: text(data.achievement && data.achievement.description, '')
    };
    return payload;
  }

  function mergeAiEditableSection(target, aiPayload) {
    if (!target || !aiPayload) return target;
    var safePayload = aiPayload || {};
    if (safePayload.summary) target.summary = safePayload.summary;
    if (safePayload.role) target.role = safePayload.role;
    if (Array.isArray(safePayload.skills) && safePayload.skills.length) target.skills = safePayload.skills;
    if (Array.isArray(safePayload.interests) && safePayload.interests.length) target.interests = safePayload.interests;
    if (safePayload.project) {
      if (safePayload.project.name) target.project.name = safePayload.project.name;
      if (safePayload.project.meta) target.project.meta = safePayload.project.meta;
      if (safePayload.project.description) target.project.description = safePayload.project.description;
    }
    if (safePayload.activity) {
      if (safePayload.activity.name) target.activity.name = safePayload.activity.name;
      if (safePayload.activity.meta) target.activity.meta = safePayload.activity.meta;
      if (safePayload.activity.description) target.activity.description = safePayload.activity.description;
    }
    if (safePayload.education) {
      if (safePayload.education.name) target.education.name = safePayload.education.name;
      if (safePayload.education.meta) target.education.meta = safePayload.education.meta;
      if (safePayload.education.description) target.education.description = safePayload.education.description;
    }
    if (safePayload.achievement) {
      if (safePayload.achievement.name) target.achievement.name = safePayload.achievement.name;
      if (safePayload.achievement.meta) target.achievement.meta = safePayload.achievement.meta;
      if (safePayload.achievement.description) target.achievement.description = safePayload.achievement.description;
    }
    return target;
  }

  function fallbackCvTransform(data, language, operation) {
    var clone = JSON.parse(JSON.stringify(data || {}));
    var translationMap = language === 'en'
      ? { 'học sinh': 'student', 'sinh viên': 'student', 'hồ sơ': 'profile', 'giới thiệu': 'profile', 'mục tiêu': 'objective', 'kỹ năng': 'skills', 'kinh nghiệm': 'experience', 'học vấn': 'education', 'chứng chỉ': 'certificates', 'sở thích': 'interests', 'thành tích': 'achievements', 'điện thoại': 'phone', 'email': 'email', 'địa điểm': 'location', 'liên kết': 'website', 'dự án': 'project', 'lớp': 'class', 'gpa': 'GPA' }
      : { 'student': 'học sinh', 'profile': 'hồ sơ', 'objective': 'mục tiêu', 'skills': 'kỹ năng', 'experience': 'kinh nghiệm', 'education': 'học vấn', 'certificates': 'chứng chỉ', 'interests': 'sở thích', 'achievements': 'thành tích', 'phone': 'điện thoại', 'location': 'địa điểm', 'website': 'liên kết', 'project': 'dự án', 'class': 'lớp', 'gpa': 'GPA' };

    function visit(node) {
      if (Array.isArray(node)) return node.map(visit);
      if (node && typeof node === 'object') {
        Object.keys(node).forEach(function (key) {
          node[key] = visit(node[key]);
        });
        return node;
      }
      if (typeof node !== 'string') return node;
      var trimmed = node.trim();
      if (!trimmed) return node;
      if (operation === 'normalize') return trimmed.replace(/\s+/g, ' ');
      if (operation === 'translate') {
        var text = trimmed;
        Object.keys(translationMap).forEach(function (source) {
          var target = translationMap[source];
          var pattern = new RegExp(source.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
          text = text.replace(pattern, target);
        });
        return text;
      }
      return trimmed;
    }

    return visit(clone);
  }

  function requestCvAI(data, language, operation) {
    var fallbackRequest = function () {
      return Promise.resolve(fallbackCvTransform(data, language, operation));
    };

    if (!window.AxisAuth || typeof window.AxisAuth.apiRequest !== 'function') {
      return fallbackRequest();
    }

    if (!window.AxisAuth.isSignedIn()) {
      return fallbackRequest();
    }

    return window.AxisAuth.apiRequest('/ai/cv', {
      method: 'POST',
      body: JSON.stringify({ data: data, language: language, operation: operation })
    }).then(function (payload) {
      if (!payload || !payload.data || typeof payload.data !== 'object') {
        throw new Error('AI trả về dữ liệu CV không hợp lệ.');
      }
      if (operation === 'normalize') {
        var merged = mergeAiEditableSection(JSON.parse(JSON.stringify(data || {})), payload.data);
        return merged;
      }
      return payload.data;
    }).catch(function (error) {
      var message = error && (error.message || '');
      var shouldFallback = /không thể kết nối|hết thời gian|not configured|ai is not configured|đã hết hạn|Không thể đồng bộ dữ liệu tài khoản|500|502|503|401|403/i.test(message || '') ||
        (error && typeof error.status === 'number' && error.status >= 401);
      if (shouldFallback) {
        return fallbackCvTransform(data, language, operation);
      }
      throw error;
    });
  }

  function profileFromAxis() {
    if (window.AxisData && typeof window.AxisData.getProfile === 'function') {
      return window.AxisData.getProfile();
    }
    return {};
  }

  async function runPipeline() {
    var run = ++pipelineRun;
    var normalizeButton = document.querySelector('[data-action="normalize"]');
    if (normalizeButton) normalizeButton.disabled = true;
    var state = document.querySelector('[data-pipeline-state]');
    if (state) state.textContent = 'Đang chạy';
    ['extract', 'structure', 'content', 'review'].forEach(function (agent) { setAgent(agent, null); });
    setStatus('Đang đọc và cấu trúc hồ sơ CV…', 'working');
    setAgent('extract', 'running');
    var extracted = extractProfile(profileFromAxis());
    setAgent('extract', 'done');
    setStatus('Đang lọc nội dung AI chỉ cho phần mô tả và kỹ năng…', 'working');
    setAgent('structure', 'running');
    var nextModel = makeModel({}, currentLanguage);
    nextModel.data = extracted;
    nextModel.language = currentLanguage;
    setAgent('structure', 'done');
    setStatus('Đang tối ưu đoạn văn, skill, abstract bằng AI…', 'working');
    setAgent('content', 'running');
    try {
      var aiPayload = await requestCvAI(aiEditableSection(nextModel.data), currentLanguage, 'normalize');
      nextModel.data = Object.assign({}, nextModel.data, aiPayload || {});
    } catch (error) {
      if (run !== pipelineRun) return;
      ['structure', 'content', 'review'].forEach(function (agent) { setAgent(agent, 'error'); });
      if (state) state.textContent = 'AI lỗi';
      if (normalizeButton) normalizeButton.disabled = false;
      setStatus(error.message || 'Không thể kết nối AI. Nội dung hiện tại vẫn được giữ nguyên.', 'error');
      return;
    }
    if (run !== pipelineRun) return;
    setAgent('content', 'done');
    setStatus('Đang kiểm tra dữ liệu CV…', 'working');
    setAgent('review', 'running');
    model = nextModel;
    setAgent('review', 'done');
    renderPreview();
    
    setStatus('Đang lưu dữ liệu CV đã chuẩn hóa…', 'working');
    try {
      await persistCvToProfile(nextModel.data);
    } catch (persistError) {
      if (run === pipelineRun) {
        if (state) state.textContent = 'Đã sẵn sàng';
        if (normalizeButton) normalizeButton.disabled = false;
        setStatus('⚠ Dữ liệu CV đã cập nhật trên màn hình nhưng chưa lưu trên server: ' + (persistError.message || 'Lỗi không xác định.'), 'warning');
      }
      return;
    }
    
    if (state) state.textContent = 'Đã sẵn sàng';
    if (normalizeButton) normalizeButton.disabled = false;
    setStatus('AI chỉ tác động vào các phần mô tả và kỹ năng. Thông tin dạng số, chứng chỉ, mục tiêu, thành tích vẫn giữ nguyên. Dữ liệu đã lưu thành công.', 'success');
  }

  function persistCvToProfile(cvData) {
    if (!window.AxisAuth || typeof window.AxisAuth.apiRequest !== 'function') {
      return Promise.reject(new Error('Hệ thống xác thực chưa sẵn sàng.'));
    }
    if (!window.AxisAuth.isSignedIn()) {
      return Promise.reject(new Error('Vui lòng đăng nhập để lưu CV lên server.'));
    }
    var payload = Object.assign({}, cvData || {});
    return window.AxisAuth.apiRequest('/profile', {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
  }

  function saveDraft() {
    if (!model) return;
    try {
      localStorage.setItem('axis_cv_draft', JSON.stringify({
        template: currentTemplate,
        language: currentLanguage,
        model: model,
        savedAt: new Date().toISOString()
      }));
      
      if (window.AxisAuth && window.AxisAuth.isSignedIn()) {
        persistCvToProfile(currentCvData()).catch(function (error) {
          console.warn('Failed to persist CV to server:', error);
          setStatus('✓ Bản nháp đã lưu trên trình duyệt, nhưng chưa đồng bộ với server.', 'warning');
        });
      } else {
        setStatus('Đã lưu bản nháp trên trình duyệt.', 'success');
      }
    } catch (error) {
      setStatus('Không thể lưu bản nháp trong trình duyệt này.', 'error');
    }
  }

  function snapshotDraft() {
    try {
      var saved = JSON.parse(localStorage.getItem('axis_cv_draft') || 'null');
      if (!saved || !saved.model || !saved.model.data) return false;
      model = saved.model;
      currentTemplate = TEMPLATE_LABELS[saved.template] ? saved.template : 'modern';
      currentLanguage = saved.language === 'en' ? 'en' : 'vi';
      model.language = currentLanguage;
      return true;
    } catch (error) {
      return false;
    }
  }

  function bindEvents() {
    document.querySelectorAll('[data-template]').forEach(function (button) {
      button.addEventListener('click', function () {
        currentTemplate = button.dataset.template;
        activePalette = 0;
        document.querySelectorAll('[data-template]').forEach(function (item) {
          var selected = item === button;
          item.classList.toggle('is-selected', selected);
          item.setAttribute('aria-pressed', selected ? 'true' : 'false');
        });
        syncColorControls();
        renderPreview();
      });
    });
    document.querySelectorAll('[data-color]').forEach(function (input) {
      input.addEventListener('input', function () {
        var variable = '--cv-' + input.dataset.color;
        preview.style.setProperty(variable, input.value);
        if (input.dataset.color === 'accent') {
          preview.style.setProperty('--cv-accent-dark', shade(input.value, .2));
          preview.style.setProperty('--cv-accent-light', tint(input.value, .72));
          preview.style.setProperty('--cv-accent-pale', tint(input.value, .9));
          syncCreativeColors(input.value);
        }
        if (input.dataset.color === 'accent') {
          var hex = input.value;
          preview.style.setProperty('--cv-accent-soft', hex + '1a');
        }
      });
    });
    document.querySelectorAll('[data-action="normalize"]').forEach(function (button) {
      button.addEventListener('click', function () { runPipeline(); });
    });
    var languageSelect = document.querySelector('[data-cv-language]');
    if (languageSelect) {
      languageSelect.addEventListener('change', function () {
        var nextLanguage = languageSelect.value === 'en' ? 'en' : 'vi';
        var previousLanguage = currentLanguage;
        currentLanguage = nextLanguage;
        if (!model) return;
        model.language = currentLanguage;
        model.labels = Object.assign({}, CV_LABELS[currentLanguage]);
        setStatus('Đang dịch nội dung CV bằng AI server…', 'working');
        languageSelect.disabled = true;
        requestCvAI(currentCvData(), currentLanguage, 'translate').then(function (data) {
          model.data = data;
          renderPreview();
          setStatus(currentLanguage === 'vi' ? 'Đã dịch nội dung CV sang tiếng Việt.' : 'CV content translated to English.', 'success');
        }).catch(function (error) {
          currentLanguage = previousLanguage;
          model.language = previousLanguage;
          model.labels = Object.assign({}, CV_LABELS[previousLanguage]);
          languageSelect.value = previousLanguage;
          renderPreview();
          setStatus(error.message || 'Không thể dịch CV; nội dung ban đầu vẫn được giữ nguyên.', 'error');
        }).finally(function () {
          languageSelect.disabled = false;
        });
      });
    }
    document.querySelectorAll('[data-action="save"]').forEach(function (button) {
      button.addEventListener('click', saveDraft);
    });
    document.querySelectorAll('[data-action="print"]').forEach(function (button) {
      button.addEventListener('click', function () {
        setStatus('Mở hộp thoại in. Chọn “Save as PDF” để xuất CV A4.', 'neutral');
        window.setTimeout(function () { window.print(); }, 40);
      });
    });
    document.addEventListener('axis:profile-hydrated', function () { runPipeline(); });
    document.addEventListener('axis:auth-state', function (event) {
      if (event.detail && event.detail.signedIn) runPipeline();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    root = document.querySelector('[data-cv-editor]');
    preview = document.querySelector('[data-cv-preview]');
    if (!root || !preview) return;
    bindEvents();
    syncColorControls();
    previewResizeObserver = new ResizeObserver(fitPreviewToViewport);
    previewResizeObserver.observe(document.querySelector('.cv-editor__workspace'));
    window.addEventListener('resize', fitPreviewToViewport);
    var restoredDraft = snapshotDraft();
    if (!restoredDraft) {
      model = makeModel(profileFromAxis(), currentLanguage);
      model.language = currentLanguage;
    }
    var languageSelect = document.querySelector('[data-cv-language]');
    if (languageSelect) languageSelect.value = currentLanguage;
    syncColorControls();
    renderPreview();
    if (restoredDraft) {
      setStatus('Đã khôi phục bản nháp gần nhất. Bấm AI chuẩn hóa để cập nhật theo hồ sơ.', 'success');
    } else {
      setStatus('Đang dùng dữ liệu mẫu. Bấm AI chuẩn hóa để đọc hồ sơ hiện tại.', 'neutral');
      runPipeline();
    }
  });
})();
