// -------------------------------------------------------------------------
    // Funciones Globales de Sanitización (XSS Defence in Depth)
    // -------------------------------------------------------------------------
    /** Carga xterm.js/css bajo demanda (383 KB que no deben pesar al arrancar). */
    let xtermLoaderPromise = null;
    function cargarXterm() {
      if (typeof Terminal !== 'undefined') return Promise.resolve();
      if (xtermLoaderPromise) return xtermLoaderPromise;
      xtermLoaderPromise = new Promise((resolve, reject) => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/css/xterm.css';
        document.head.appendChild(link);
        const script = document.createElement('script');
        script.src = '/static/js/xterm.js';
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('No se pudo cargar xterm.js'));
        document.head.appendChild(script);
      });
      return xtermLoaderPromise;
    }

    function escapeHtml(str) {
      if (str == null) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // -------------------------------------------------------------------------
    // Catálogo Oficial del Tech Stack SISPER (CDN Oficiales + Fallbacks Offline)
    // -------------------------------------------------------------------------
    const TECH_CDN_URLS = {
      docker: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg',
      podman: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/podman/podman-original.svg',
      kubernetes: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/kubernetes/kubernetes-plain.svg',
      k8s: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/kubernetes/kubernetes-plain.svg',
      django: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/django/django-plain.svg',
      python: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg',
      webpack: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/webpack/webpack-original.svg',
      react: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg',
      postgresql: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg',
      postgres: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg',
      mongodb: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mongodb/mongodb-original.svg',
      mongo: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mongodb/mongodb-original.svg',
      redis: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/redis/redis-original.svg',
      keydb: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/redis/redis-original.svg',
      rabbitmq: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/rabbitmq/rabbitmq-original.svg',
      git: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/git/git-original.svg',
      gitlab: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/gitlab/gitlab-original.svg',
      keycloak: 'https://cdn.simpleicons.org/keycloak/4A90E2',
      onlyoffice: 'https://cdn.simpleicons.org/onlyoffice/FF6F3D',
      alfresco: 'https://cdn.simpleicons.org/alfresco/002B49',
      celery: 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/celery/celery-original.svg'
    };

    const TECH_FALLBACK_SVG = {
      python: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#387eb8" d="M11.914 0C5.82 0 6.2 2.656 6.2 2.656l.006 2.753h5.814v.826H3.84S0 5.766 0 11.879c0 6.115 3.344 5.925 3.344 5.925h1.996v-2.81c0-3.22 2.74-3.22 2.74-3.22h5.753c2.617 0 2.516-2.48 2.516-2.48V3.41s.385-3.41-4.435-3.41zm-3.15 1.705a1.003 1.003 0 1 1 0 2.006 1.003 1.003 0 0 1 0-2.006z"/><path fill="#ffe873" d="M12.086 24c6.094 0 5.714-2.656 5.714-2.656l-.006-2.753H11.98v-.826h8.18s3.84.469 3.84-5.644c0-6.115-3.344-5.925-3.344-5.925h-1.996v2.81c0 3.22-2.74 3.22-2.74 3.22H10.2c-2.617 0-2.516 2.48-2.516 2.48v5.895s-.385 3.409 4.436 3.409zm3.15-1.705a1.003 1.003 0 1 1 0-2.006 1.003 1.003 0 0 1 0 2.006z"/></svg>`,
      django: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#44B78B" d="M11.146 0h3.333v16.893c-1.577.303-2.88.455-3.908.455-2.607 0-4.334-.849-5.183-2.546-.576-1.152-.864-2.713-.864-4.683 0-2.091.333-3.759 1-5.002.849-1.576 2.425-2.364 4.728-2.364.303 0 .606.015.894.045V0zm0 5.562c-.273-.03-.546-.045-.819-.045-1.303 0-2.228.455-2.773 1.364-.424.728-.637 1.804-.637 3.229 0 1.485.213 2.576.637 3.274.545.88 1.47 1.319 2.773 1.319.273 0 .546-.015.819-.045V5.562zM2.758 7.397H6.09v12.23H2.758V7.397zm-.212-4.183C2.546 2.122 2.925 1.7 3.683 1.7c.758 0 1.137.424 1.137 1.273 0 .849-.379 1.273-1.137 1.273-.758 0-1.137-.424-1.137-1.273zm18.307 4.183h3.334v12.23h-3.334V7.397zm-.212-4.183c0-1.092.379-1.516 1.137-1.516.758 0 1.137.424 1.137 1.273 0 .849-.379 1.273-1.137 1.273-.758 0-1.137-.424-1.137-1.273z"/></svg>`,
      react: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><circle cx="12" cy="12" r="2.2" fill="#61DAFB"/><ellipse cx="12" cy="12" rx="10" ry="3.8" stroke="#61DAFB" stroke-width="1.3" fill="none" transform="rotate(0 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="3.8" stroke="#61DAFB" stroke-width="1.3" fill="none" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="3.8" stroke="#61DAFB" stroke-width="1.3" fill="none" transform="rotate(120 12 12)"/></svg>`,
      webpack: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><polygon points="12 1.5 21.5 7 21.5 17 12 22.5 2.5 17 2.5 7" fill="none" stroke="#1C78C0" stroke-width="1.4" stroke-linejoin="round"/><polygon points="12 1.5 21.5 7 12 12.5 2.5 7" fill="#8DD6F9" fill-opacity="0.35"/><polygon points="12 12.5 21.5 7 21.5 17 12 22.5" fill="#1C78C0" fill-opacity="0.5"/><polygon points="2.5 7 12 12.5 12 22.5 2.5 17" fill="#1C78C0" fill-opacity="0.75"/><polygon points="12 6.5 17 9.5 17 14.5 12 17.5 7 14.5 7 9.5" fill="#1C78C0" stroke="#8DD6F9" stroke-width="0.8" stroke-linejoin="round"/><polygon points="12 6.5 17 9.5 12 12 7 9.5" fill="#8DD6F9"/><polygon points="12 12 17 9.5 17 14.5 12 17.5" fill="#4695D6"/><polygon points="7 9.5 12 12 12 17.5 7 14.5" fill="#2B72B5"/></svg>`,
      kubernetes: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#326CE5" d="M11.666 0a1.44 1.44 0 0 0-.585.155L2.83 5.093a1.444 1.444 0 0 0-.722 1.25v9.88c0 .52.274.997.722 1.254l8.251 4.938c.45.268.995.27 1.442.007l8.368-4.945a1.447 1.447 0 0 0 .734-1.253V6.343a1.444 1.444 0 0 0-.722-1.25L12.923.155A1.44 1.44 0 0 0 12.339 0h-.673zm.332 2.146l7.472 4.417v8.868l-7.472 4.417-7.472-4.417V6.563l7.472-4.417zm.002 2.193a.987.987 0 0 0-.498.135l-2.015 1.164a.99.99 0 0 0-.363.363l-.707 1.226a.985.985 0 0 0-.131.498v2.328c0 .174.045.345.131.498l.707 1.225c.097.168.232.308.397.403l2.015 1.164a.988.988 0 0 0 .988 0l2.015-1.164a.991.991 0 0 0 .397-.403l.707-1.225a.987.987 0 0 0 .131-.498V9.731a.987.987 0 0 0-.131-.498l-.707-1.226a.99.99 0 0 0-.397-.363l-2.015-1.164a.986.986 0 0 0-.464-.135zm0 1.979l1.494.863.525.91-.525.909-1.494.863-1.494-.863-.525-.91.525-.909 1.494-.863z"/></svg>`,
      k8s: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#326CE5" d="M11.666 0a1.44 1.44 0 0 0-.585.155L2.83 5.093a1.444 1.444 0 0 0-.722 1.25v9.88c0 .52.274.997.722 1.254l8.251 4.938c.45.268.995.27 1.442.007l8.368-4.945a1.447 1.447 0 0 0 .734-1.253V6.343a1.444 1.444 0 0 0-.722-1.25L12.923.155A1.44 1.44 0 0 0 12.339 0h-.673zm.332 2.146l7.472 4.417v8.868l-7.472 4.417-7.472-4.417V6.563l7.472-4.417zm.002 2.193a.987.987 0 0 0-.498.135l-2.015 1.164a.99.99 0 0 0-.363.363l-.707 1.226a.985.985 0 0 0-.131.498v2.328c0 .174.045.345.131.498l.707 1.225c.097.168.232.308.397.403l2.015 1.164a.988.988 0 0 0 .988 0l2.015-1.164a.991.991 0 0 0 .397-.403l.707-1.225a.987.987 0 0 0 .131-.498V9.731a.987.987 0 0 0-.131-.498l-.707-1.226a.99.99 0 0 0-.397-.363l-2.015-1.164a.986.986 0 0 0-.464-.135zm0 1.979l1.494.863.525.91-.525.909-1.494.863-1.494-.863-.525-.91.525-.909 1.494-.863z"/></svg>`,
      rabbitmq: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#FF6600" d="M10.36 0c-1.89 0-3.42 1.53-3.42 3.42v5.77A6.47 6.47 0 0 0 3.39 12a6.49 6.49 0 0 0-.25 1.78c0 3.58 2.91 6.49 6.49 6.49h7.73c3.58 0 6.49-2.91 6.49-6.49 0-3.32-2.5-6.07-5.74-6.44V3.42C18.11 1.53 16.58 0 14.69 0a3.39 3.39 0 0 0-2.16.78A3.39 3.39 0 0 0 10.36 0zm0 1.83c.88 0 1.59.71 1.59 1.59v6.86c-.52.23-1 .54-1.43.91V3.42c0-.88-.71-1.59-1.59-1.59s-1.59.71-1.59 1.59v8.6c-.44.82-.69 1.76-.69 2.76 0 2.57 2.09 4.66 4.66 4.66h6.06c2.57 0 4.66-2.09 4.66-4.66s-2.09-4.66-4.66-4.66h-.56V3.42c0-.88-.71-1.59-1.59-1.59s-1.59.71-1.59 1.59v4.29a3.3 3.3 0 0 0-1.84.42V3.42c0-.88.71-1.59 1.59-1.59zm6.73 9.47a1.07 1.07 0 1 1 0 2.14 1.07 1.07 0 0 1 0-2.14z"/></svg>`,
      celery: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#94C83D" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1.2 4.2c1.7 0 3.2.98 3.96 2.41.33.63.53 1.36.53 2.12 0 2.39-1.81 4.36-4.14 4.53l.85 3.55-1.58.38-1.07-4.46c-1.84-.35-3.23-1.97-3.23-3.91 0-2.2 1.78-3.99 3.97-3.99.24 0 .47.03.71.07z"/><circle cx="12.5" cy="10.8" r="1.5" fill="#37814A"/></svg>`,
      postgresql: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#336791" d="M11.654 0c-2.85 0-5.467 1.272-6.626 3.267-.532.915-.79 1.944-.813 2.977l-.01.075c-.838.271-1.58.74-2.164 1.373C.685 9.117.002 10.97.002 13.064c0 3.125 1.492 5.836 3.774 7.21l.307.185v-1.758c0-.687.275-1.346.764-1.832.488-.485 1.152-.758 1.844-.758.127 0 .254.01.379.028a3.17 3.17 0 0 0 1.83-.342c.574-.34.98-.87 1.15-1.498.118-.439.115-.898-.01-1.332a2.38 2.38 0 0 0-.684-1.037 2.45 2.45 0 0 0-1.222-.52c-.65-.102-1.314.032-1.874.378-.45.277-.978.423-1.517.42-.705-.004-1.378-.29-1.87-.793a2.68 2.68 0 0 1-.767-1.93c0-1.488.58-2.805 1.536-3.687.585-.539 1.315-.897 2.11-1.035.434-.075.875-.078 1.31-.008.21.034.42.085.626.152.19.062.38.138.563.228.375.184.72.417 1.03.693.307.274.577.586.8.932l.24.37.382-.218c.613-.35 1.314-.543 2.029-.558.715-.015 1.423.15 2.046.478.623.327 1.144.81 1.507 1.397.362.587.544 1.264.526 1.956-.017.693-.232 1.364-.62 1.938a4.11 4.11 0 0 1-1.47 1.376c-.615.337-1.315.498-2.023.465a3.86 3.86 0 0 1-.58-.088c-.287-.076-.563-.186-.819-.328-.256-.14-.482-.315-.67-.518a2.15 2.15 0 0 1-.456-.73c-.098-.276-.123-.57-.073-.86.05-.29.173-.56.357-.786.184-.226.425-.398.7-.5.275-.102.571-.128.86-.076.29.052.557.178.778.366.222.188.388.434.484.713.045.132.062.27.05.408-.013.138-.056.27-.128.388-.072.118-.17.218-.288.293a.85.85 0 0 1-.416.126.82.82 0 0 1-.42-.112.8.8 0 0 1-.295-.29.78.78 0 0 1-.09-.413c.01-.143.06-.279.145-.39.085-.113.199-.196.328-.242a.54.54 0 0 1 .37-.015c.123.04.228.12.3.226.072.106.103.232.088.358a.4.4 0 0 1-.082.203.38.38 0 0 1-.18.128.37.37 0 0 1-.225 0 .36.36 0 0 1-.168-.11.35.35 0 0 1-.06-.188c0-.065.023-.127.065-.174a.23.23 0 0 1 .168-.07.24.24 0 0 1 .172.065c.045.045.07.106.07.17 0 .064-.025.125-.07.17a.24.24 0 0 1-.172.065.23.23 0 0 1-.168-.07.24.24 0 0 1-.065-.17c0-.064.025-.125.07-.17a.23.23 0 0 1 .168-.07c.065 0 .127.025.172.07.045.045.07.106.07.17z"/></svg>`,
      postgres: (s=16) => TECH_FALLBACK_SVG.postgresql(s),
      mongodb: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#47A248" d="M17.193 9.555c-1.264-5.9-4.282-8.497-4.896-9.555-.214.613-.67 1.804-.98 2.583-2.02 5.07-4.388 7.394-4.57 11.23-.207 4.316 2.584 7.697 5.253 9.87.502.408.874.317 1.05.083.567-.756 1.956-2.616 2.77-4.223 1.956-3.86 1.996-6.84 1.373-9.988zm-5.011 11.838v-8.204c0-.28.225-.506.505-.506.28 0 .506.226.506.506v8.204c0 .28-.226.506-.506.506-.28 0-.505-.226-.505-.506z"/></svg>`,
      mongo: (s=16) => TECH_FALLBACK_SVG.mongodb(s),
      redis: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#DC382D" d="M22.56 6.84a1.86 1.86 0 0 0-.9-.55L12.72 3.1a1.83 1.83 0 0 0-1.44 0L2.34 6.29a1.86 1.86 0 0 0-.9.55 1.76 1.76 0 0 0-.44 1.15v8.02a1.76 1.76 0 0 0 .44 1.15 1.86 1.86 0 0 0 .9.55l8.94 3.19a1.83 1.83 0 0 0 1.44 0l8.94-3.19a1.86 1.86 0 0 0 .9-.55 1.76 1.76 0 0 0 .44-1.15V7.99a1.76 1.76 0 0 0-.44-1.15zM12 4.67l7.55 2.69L17.7 8.04 12 6.01 6.3 8.04 4.45 7.36 12 4.67zm0 14.66l-7.55-2.69v-5.6l3.77 1.35a1.83 1.83 0 0 0 1.44 0L12 11.6l2.34.79a1.83 1.83 0 0 0 1.44 0l3.77-1.35v5.6L12 19.33z"/></svg>`,
      keydb: (s=16) => TECH_FALLBACK_SVG.redis(s),
      keycloak: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#008A87" d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 3.6c2.08 0 3.93.81 5.31 2.13L12 11.04 6.69 5.73A7.16 7.16 0 0 1 12 3.6zm-7.2 4.71L10.08 13.6 4.77 18.91A7.16 7.16 0 0 1 4.8 8.31zm8.49 12.09c-2.08 0-3.93-.81-5.31-2.13L13.29 12.96l5.31 5.31c-1.38 1.32-3.23 2.13-6.6 2.13zm5.91-4.71L13.92 10.4l5.31-5.31c1.23 1.41 1.97 3.24 1.97 5.31s-.74 3.9-1.97 5.31z"/></svg>`,
      onlyoffice: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><rect width="24" height="24" rx="4" fill="#FF6F3D"/><rect x="5" y="5.5" width="14" height="2.5" rx="0.5" fill="#FFFFFF"/><rect x="5" y="10.5" width="14" height="2.5" rx="0.5" fill="#FFFFFF"/><rect x="5" y="15.5" width="9" height="2.5" rx="0.5" fill="#FFFFFF"/></svg>`,
      git: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#F05032" d="M23.546 10.93L13.067.452c-.604-.603-1.582-.603-2.188 0L8.708 2.627l2.76 2.76c.645-.215 1.379-.07 1.889.441.516.515.658 1.258.438 1.9l3.167 3.167c.642-.22 1.385-.077 1.9.438.78.78.78 2.05 0 2.831-.78.781-2.05.781-2.83 0-.57-.57-.704-1.393-.404-2.072l-2.952-2.953v6.793c.182.086.354.205.497.35.782.78.782 2.05 0 2.831-.782.78-2.05.78-2.831 0-.78-.78-.78-2.05 0-2.83.18-.18.39-.31.62-.39v-6.85a2.02 2.02 0 0 1-.62-.39c-.56-.56-.7-1.37-.41-2.04L6.96 5.86.454 12.37c-.605.605-.605 1.584 0 2.189l10.48 10.477c.604.604 1.582.604 2.186 0l10.426-10.43c.605-.603.605-1.582 0-2.186v.01z"/></svg>`,
      gitlab: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#FC6D26" d="m23.6 9.59-1.28-3.95a.94.94 0 0 0-.36-.45.96.96 0 0 0-.58-.16.98.98 0 0 0-.57.17.93.93 0 0 0-.34.44L18.8 10.7H5.2L3.53 5.64a.93.93 0 0 0-.34-.44.98.98 0 0 0-.57-.17.96.96 0 0 0-.58.16.94.94 0 0 0-.36.45L.4 9.59a1.35 1.35 0 0 0 .49 1.51L12 19.33l11.11-8.23a1.35 1.35 0 0 0 .49-1.51z"/></svg>`,
      docker: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#2496ED" d="M13.983 11.078h2.119a.186.186 0 0 0 .186-.185V9.006a.186.186 0 0 0-.186-.186h-2.119a.185.185 0 0 0-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 0 0 .186-.186V3.574a.186.186 0 0 0-.186-.185h-2.118a.185.185 0 0 0-.185.185v1.888c0 .102.082.186.185.186m0 2.716h2.118a.187.187 0 0 0 .186-.186V6.29a.186.186 0 0 0-.186-.185h-2.118a.185.185 0 0 0-.185.185v1.887c0 .102.082.186.185.186m-2.93 0h2.12a.186.186 0 0 0 .184-.186V6.29a.185.185 0 0 0-.185-.185H8.1a.185.185 0 0 0-.185.185v1.887c0 .102.083.186.185.186m-2.964 0h2.119a.186.186 0 0 0 .185-.186V6.29a.185.185 0 0 0-.185-.185H5.136a.186.186 0 0 0-.186.185v1.887c0 .102.084.186.186.186m5.893 2.715h2.12a.186.186 0 0 0 .185-.185V9.006a.186.186 0 0 0-.185-.186h-2.12a.185.185 0 0 0-.184.185v1.888c0 .102.083.185.184.185m-2.93 0h2.12a.185.185 0 0 0 .184-.185V9.006a.185.185 0 0 0-.184-.186h-2.12a.185.185 0 0 0-.184.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 0 0 .185-.185V9.006a.185.185 0 0 0-.185-.186h-2.12a.185.185 0 0 0-.185.185v1.888c0 .102.084.185.186.185m-2.928 0h2.119a.185.185 0 0 0 .185-.185V9.006a.185.185 0 0 0-.185-.186H2.208a.186.186 0 0 0-.186.185v1.888c0 .102.084.185.186.185m21.75 1.543c-.413-.263-1.63-.385-2.614-.144-.142-.71-.62-1.33-1.306-1.67-.184-.09-.378-.146-.576-.174l-.234-.033-.11.21c-.42.802-.455 1.776-.098 2.616-.275.143-.598.24-.967.283-.43.05-.88.026-1.328-.073l-.448-.098-.24.394c-.815 1.34-2.102 2.274-3.626 2.63-1.428.334-2.924.234-4.32-.29l-.265-.1-.21.2a10.82 10.82 0 0 1-5.182 2.697c-1.444.336-2.946.28-4.35-.164l-.452-.143-.09.464c.294 1.52 1.096 2.89 2.29 3.916 1.304 1.12 2.94 1.764 4.675 1.838 7.42.316 13.918-4.324 15.688-11.17l.08-.31-.303-.133z"/></svg>`,
      podman: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="#892CA0" d="M12.002 0c-4.66 0-8.528 2.87-10.378 7.02A12.023 12.023 0 0 0 0 12.002c0 1.77.387 3.45 1.08 4.962 1.848 4.028 5.703 6.91 10.323 7.034.2.005.398.005.599.002 4.62-.124 8.475-3.006 10.323-7.034.693-1.512 1.08-3.192 1.08-4.962a12.023 12.023 0 0 0-1.624-4.982C19.933 2.87 16.662 0 12.002 0zm-3.04 7.64c.82 0 1.485.665 1.485 1.485 0 .82-.665 1.485-1.485 1.485-.82 0-1.485-.665-1.485-1.485 0-.82.665-1.485 1.485-1.485zm6.08 0c.82 0 1.485.665 1.485 1.485 0 .82-.665 1.485-1.485 1.485-.82 0-1.485-.665-1.485-1.485 0-.82.665-1.485 1.485-1.485zm-3.04 4.88c2.46 0 4.56 1.42 5.56 3.48H6.48c1-2.06 3.1-3.48 5.56-3.48z"/></svg>`,
      alfresco: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><rect width="24" height="24" rx="4" fill="#0284c7" fill-opacity="0.18" stroke="#0284c7" stroke-width="1.2"/><path fill="#38bdf8" d="M6 7.5h12v2H6zm0 4h12v2H6zm0 4h8v2H6z"/><circle cx="17.5" cy="16.5" r="2" fill="#38bdf8"/></svg>`,
      firmador: (s=16) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" class="tech-icon-svg" style="vertical-align:middle; flex-shrink:0;"><path fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="m9 12 2 2 4-4"/></svg>`
    };

    /* Iconos cuyo CDN es una variante monocroma con relleno OSCURO: sobre el
       tema oscuro no se ven (django-plain.svg pinta en #092E20).  Para éstos se
       usa el SVG local, que ya trae el color de marca visible (#44B78B). */
    const TECH_PREFER_LOCAL = new Set(['django']);

    function getTechIcon(name, size = 16) {
      if (!name) return '';
      const key = String(name).toLowerCase().trim();
      const cdnUrl = TECH_PREFER_LOCAL.has(key) ? null : TECH_CDN_URLS[key];
      const fallbackRenderer = TECH_FALLBACK_SVG[key];
      const fallbackSvg = fallbackRenderer ? fallbackRenderer(size) : '';

      if (!cdnUrl && !fallbackSvg) return '';
      if (!cdnUrl) {
        /* Icono local: se le pone un fondo tenue para que un trazo oscuro (el
           verde de Django) no se pierda sobre la tarjeta oscura. */
        return `<span class="tech-icon-wrapper tech-icon-chip" style="width:${size}px; height:${size}px;" title="${key}">${fallbackSvg}</span>`;
      }

      return `<span class="tech-icon-wrapper" style="width:${size}px; height:${size}px;" title="${key}">` +
        `<img src="${cdnUrl}" width="${size}" height="${size}" class="tech-icon-img" alt="${key}" loading="lazy" ` +
        `style="width:${size}px; height:${size}px; object-fit:contain; vertical-align:middle; display:inline-block;" ` +
        `onerror="this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.style.display='inline-flex';" />` +
        `<span class="tech-fallback-svg" style="display:none; width:${size}px; height:${size}px;">${fallbackSvg}</span>` +
        `</span>`;
    }

    // Proxy para retrocompatibilidad total con llamadas TECH_ICONS[key](size)
    const TECH_ICONS = new Proxy(TECH_FALLBACK_SVG, {
      get(target, prop) {
        if (typeof prop === 'string') {
          return (s=16) => getTechIcon(prop, s);
        }
        return target[prop];
      }
    });

    // -------------------------------------------------------------------------
    // Control de Roles y Autenticación RBAC (Opción A: PIN / Token)
    // -------------------------------------------------------------------------
    let currentUserRole = localStorage.getItem('sisper_auth_role') || 'viewer';
    let adminSessionToken = localStorage.getItem('sisper_auth_token') || '';
    let pendingAdminCallback = null;

    function getAuthHeaders(customHeaders = {}) {
      const h = { ...customHeaders, 'X-Auth-Role': currentUserRole };
      if (adminSessionToken) h['X-Auth-Token'] = adminSessionToken;
      return h;
    }

    function openRoleModal(reasonMsg = null) {
      const reasonEl = document.getElementById('roleModalReason');
      if (reasonMsg) {
        reasonEl.innerText = reasonMsg;
        reasonEl.style.display = 'block';
      } else {
        reasonEl.style.display = 'none';
      }

      const radio = document.querySelector(`input[name="roleRadio"][value="${currentUserRole}"]`);
      if (radio) radio.checked = true;
      selectRoleRadio(currentUserRole);

      document.getElementById('btnRoleLogoutAdmin').style.display = (currentUserRole === 'admin') ? 'inline-flex' : 'none';
      document.getElementById('rolePinInput').value = '';
      document.getElementById('rolePinError').style.display = 'none';
      document.getElementById('roleModal').style.display = 'flex';
    }

    function closeRoleModal() {
      document.getElementById('roleModal').style.display = 'none';
      pendingAdminCallback = null;
    }

    function selectRoleRadio(role) {
      const pinContainer = document.getElementById('rolePinContainer');
      const pinInput = document.getElementById('rolePinInput');
      const pinError = document.getElementById('rolePinError');
      pinError.style.display = 'none';

      /* Admin y Desarrollador entran con PIN; Soporte/QA es de sólo lectura y
         no lo necesita. */
      const pidePin = (role === 'admin' && currentUserRole !== 'admin')
        || (role === 'dev' && currentUserRole !== 'dev');
      if (pidePin) {
        pinContainer.style.display = 'block';
        setTimeout(() => pinInput.focus(), 150);
      } else {
        pinContainer.style.display = 'none';
      }
    }

    async function submitRoleChange() {
      const selected = document.querySelector('input[name="roleRadio"]:checked')?.value || 'dev';
      const pinError = document.getElementById('rolePinError');

      /* Admin y Desarrollador piden PIN (el rol es una credencial, no un adorno);
         Soporte/QA es de sólo lectura y no lo necesita.  Si ya eres admin, bajar
         de rol no requiere volver a autenticarse. */
      const pidePin = selected !== 'viewer' && currentUserRole !== 'admin';
      if (pidePin) {
        const pin = document.getElementById('rolePinInput').value.trim();
        if (!pin) {
          pinError.innerText = "⚠️ Ingresa el PIN para entrar con ese perfil.";
          pinError.style.display = 'block';
          return;
        }

        try {
          const res = await fetch('/api/auth/verify_pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: pin, role: selected })
          });
          const data = await res.json();
          /* Desarrollador entra sin token elevado: sólo admin recibe token. */
          if (data.success && (data.token || selected === 'dev')) {
            currentUserRole = selected;
            localStorage.setItem('sisper_auth_role', selected);
            if (selected === 'admin' && data.token) {
              /* Sólo el admin conserva el token de sesión elevada. */
              adminSessionToken = data.token;
              localStorage.setItem('sisper_auth_token', data.token);
            }
            updateRoleUI();
            closeRoleModal();
            showToast(selected === 'admin'
              ? "Perfil actualizado: Administrador / DevOps 👑"
              : "Perfil actualizado: Desarrollador 👨‍💻");
            if (pendingAdminCallback) {
              const cb = pendingAdminCallback;
              pendingAdminCallback = null;
              cb();
            }
          } else {
            pinError.innerText = data.message || "⚠️ PIN incorrecto.";
            pinError.style.display = 'block';
          }
        } catch (e) {
          pinError.innerText = "Error verificando PIN con el servidor.";
          pinError.style.display = 'block';
        }
      } else {
        currentUserRole = selected;
        localStorage.setItem('sisper_auth_role', selected);
        updateRoleUI();
        closeRoleModal();
        showToast(`Perfil cambiado a: ${selected.toUpperCase()}`);
      }
    }

    async function logoutAdminRole() {
      try {
        if (adminSessionToken) {
          fetch('/api/auth/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: adminSessionToken })
          }).catch(() => {});
        }
      } catch (e) {}
      currentUserRole = 'viewer';
      adminSessionToken = '';
      localStorage.setItem('sisper_auth_role', 'dev');
      localStorage.removeItem('sisper_auth_token');
      updateRoleUI();
      closeRoleModal();
      showToast("Sesión de Administrador cerrada. Perfil activo: Desarrollador.");
    }

    async function validateAuthSession() {
      if (currentUserRole === 'admin') {
        if (!adminSessionToken) {
          currentUserRole = 'viewer';
          localStorage.setItem('sisper_auth_role', 'dev');
          updateRoleUI();
          return;
        }
        try {
          const res = await fetch('/api/auth/validate_session', {
            headers: getAuthHeaders()
          });
          if (res.ok) {
            const data = await res.json();
            if (!data.valid) {
              currentUserRole = 'viewer';
              adminSessionToken = '';
              localStorage.setItem('sisper_auth_role', 'dev');
              localStorage.removeItem('sisper_auth_token');
              updateRoleUI();
              showToast("ℹ️ Sesión de Administrador expirada. Iniciando en modo Desarrollador.");
            }
          }
        } catch (e) {
          console.warn("Error validando sesión:", e);
        }
      }
    }

    /*: Pestañas que ve cada rol.  ``null`` = todas.  Las pestañas que no están
       en la lista quedan ocultas, igual que las etiquetas de sección que se
       queden sin ningún elemento visible. */
    const ROL_PESTANAS = {
      viewer: ['k8s', 'map', 'activity'],
      dev: ['services', 'consoles', 'workspace', 'k8s', 'infra', 'map', 'activity'],
      admin: null,
    };

    function aplicarPermisosDeRol() {
      const permitidas = ROL_PESTANAS[currentUserRole];
      document.querySelectorAll('.sidebar-nav-item[data-tab]').forEach((btn) => {
        const tab = btn.getAttribute('data-tab');
        btn.style.display = (!permitidas || permitidas.includes(tab)) ? '' : 'none';
      });
      /* Una etiqueta de sección sin elementos visibles debajo no pinta nada. */
      document.querySelectorAll('.sidebar-section-label').forEach((label) => {
        let visible = false;
        let nodo = label.nextElementSibling;
        while (nodo && !nodo.classList.contains('sidebar-section-label')) {
          if (nodo.classList.contains('sidebar-nav-item')) {
            if (nodo.style.display !== 'none') { visible = true; break; }
          } else if (nodo.classList.contains('sidebar-divider')) {
            /* los divisores separan grupos: se decide por los elementos vistos */
          }
          nodo = nodo.nextElementSibling;
        }
        label.style.display = visible ? '' : 'none';
      });
      /* Soporte / QA es sólo lectura de monitoreo: no necesita la cinta de KPIs
         (BE/FE/bajar/subir/sucios…), ni las insignias de entorno, ni el selector
         de carpeta raíz, ni el Layout Studio de Tilix. */
      const esViewer = currentUserRole === 'viewer';
      ['kpiRibbon', 'globalEnvSwitcher', 'baseDirPathBtn'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.style.display = esViewer ? 'none' : '';
      });
      document.querySelectorAll('.sidebar-footer-btn').forEach((b) => {
        const accion = b.getAttribute('onclick') || '';
        if (accion.includes('openLayoutStudioModal') || accion.includes('openRootFolderModal')) {
          b.style.display = esViewer ? 'none' : '';
        }
      });
      /* Las acciones que mutan el clúster siguen siendo de Administrador. */
      document.querySelectorAll('#tab-k8s button').forEach((b) => {
        const accion = b.getAttribute('onclick') || '';
        if (/restart|rollout|deploy|eliminar|delete/i.test(accion)) {
          b.disabled = esViewer;
          b.style.opacity = esViewer ? '0.45' : '';
          b.title = esViewer ? 'Requiere rol Desarrollador o Administrador' : (b.title || '');
        }
      });

      /* Si la pestaña abierta deja de estar permitida, se cae a una que sí lo esté. */
      const activo = document.querySelector('.tab-pane.active');
      if (activo) {
        const id = activo.id.replace('tab-', '');
        if (permitidas && !permitidas.includes(id)) {
          const primera = permitidas.find((t) => document.querySelector(`.sidebar-nav-item[data-tab="${t}"]`));
          if (primera) switchTab(primera, document.querySelector(`.sidebar-nav-item[data-tab="${primera}"]`));
        }
      }
    }

    /*: El muro estiraba cada fila al alto disponible, así que el cuerpo de la
       consola quedaba en 14,5 líneas y la última salía **cortada**.  Ahora el
       panel mide un número entero de líneas: se fija `--cw-rows` y el CSS
       calcula el alto.  Un solo cálculo, sin realimentación. */
    function ajustarFilasDeConsola() {
      const grid = document.querySelector('#tab-consoles .console-mosaic-grid');
      if (!grid) return;
      const fuente = parseFloat(getComputedStyle(grid).getPropertyValue('--cw-font-size'))
        || consoleWorkspace.wallFontSize || 11;
      const interlinea = parseFloat(getComputedStyle(grid).getPropertyValue('--cw-line-height')) || 1.5;
      const lh = fuente * interlinea;
      if (!lh) return;
      /* Cuerpo de ~200 px y **líneas enteras**: el alto del panel se calcula en
         el CSS con `--cw-rows`, así que no hay fila a medias (texto cortado). */
      grid.style.setProperty('--cw-rows', String(Math.max(6, Math.floor(200 / lh))));
    }

    function updateRoleUI() {
      const badge = document.getElementById('headerRoleBadge');
      if (badge) {
        if (currentUserRole === 'admin') {
          badge.className = 'badge-role-admin';
          badge.innerHTML = '👑 ADMIN / DEVOPS';
        } else if (currentUserRole === 'viewer') {
          badge.className = 'badge-role-viewer';
          badge.innerHTML = '👁️ SOPORTE / QA';
        } else {
          currentUserRole = 'viewer';
          badge.className = 'badge-role-dev';
          badge.innerHTML = '👨‍💻 DESARROLLADOR';
        }
      }

      // Sincronizar footer de la sidebar
      const sideRoleLabel = document.getElementById('sidebarRoleLabel');
      const sideRoleIcon = document.getElementById('sidebarRoleIcon');
      const sideRolePill = document.getElementById('sidebarRolePill');
      if (sideRoleLabel && sideRoleIcon) {
        if (currentUserRole === 'admin') {
          sideRoleLabel.innerText = 'Admin / DevOps';
          sideRoleIcon.innerText = '👑';
          if (sideRolePill) sideRolePill.style.borderColor = 'rgba(245, 158, 11, 0.45)';
        } else if (currentUserRole === 'viewer') {
          sideRoleLabel.innerText = 'Soporte / QA';
          sideRoleIcon.innerText = '👁️';
          if (sideRolePill) sideRolePill.style.borderColor = 'rgba(148, 163, 184, 0.35)';
        } else {
          sideRoleLabel.innerText = 'Desarrollador';
          sideRoleIcon.innerText = '👨‍💻';
          if (sideRolePill) sideRolePill.style.borderColor = 'rgba(56, 189, 248, 0.4)';
        }
      }

      // Ocultar / Mostrar pestaña Deployments & Versiones según rol
      const tabDep = document.getElementById('tabLinkDeployments') || document.querySelector('.tab-link[data-tab="deployments"]');
      if (tabDep) {
        tabDep.style.display = (currentUserRole === 'admin') ? '' : 'none';
      }
      const activeTab = document.querySelector('.tab-pane.active');
      if (activeTab && activeTab.id === 'tab-deployments' && currentUserRole !== 'admin') {
        switchTab('services');
      }

      // Ocultar cajas de mutación de Entorno y Bitácora para roles no-admin
      const boxEnv = document.getElementById('boxModoEntorno');
      if (boxEnv) boxEnv.style.display = (currentUserRole === 'admin') ? '' : 'none';
      const boxBit = document.getElementById('boxBitacora');
      if (boxBit) boxBit.style.display = (currentUserRole === 'admin') ? '' : 'none';

      // Pestañas y secciones según el rol (Soporte/QA y Desarrollador acotados)
      aplicarPermisosDeRol();
    }

    function ensureAdminAuth(actionCallback, reasonMsg = null) {
      if (currentUserRole === 'admin' && adminSessionToken) {
        actionCallback();
      } else {
        pendingAdminCallback = actionCallback;
        openRoleModal(reasonMsg || "🔒 Esta acción requiere permisos de Administrador / DevOps. Ingresa el PIN para continuar.");
      }
    }

    function ensureDevOrAdminAuth(actionCallback) {
      if (currentUserRole === 'viewer') {
        showToast("⚠️ Acción no permitida para el rol Soporte / QA (Solo Lectura).");
        openRoleModal("El rol Soporte / QA es de solo lectura. Selecciona Desarrollador o Administrador para ejecutar acciones.");
        return false;
      }
      if (actionCallback) actionCallback();
      return true;
    }

    let globalData = { backend: [], frontend: [], infra: {}, env: {} };
    let currentSlice = 'all';
    let pendingGit = { service: '', action: '' };
    let pendingBranchService = { name: '', port: 0 };
    let pendingEnvTarget = 'develop';
    let currentLogTarget = { name: '', namespace: '', rawText: '' };
    let logAutoInterval = null;
    let editVersionTarget = { service: '', env: 'develop' };
    // Marca de tiempo (epoch, tal como la envía el servidor) del último evento
    // de .env ya notificado.  null = todavía sin línea base: la primera lectura
    // adopta el evento más reciente en lugar de notificar el historial
    // acumulado que el servidor conserva de todos modos.
    let lastHandledEnvWatcherTs = null;

    /**
     * Diagnóstico del muro desde la consola del navegador.
     *
     * Devuelve una línea por consola (visibilidad, hidratación, líneas, marcador
     * de estado y pie) más la **versión de la interfaz cargada** frente a la que
     * sirve el servidor: si no coinciden, el navegador tiene una copia vieja.
     */
    function diagnosticoMuro() {
      const filas = Array.from(document.querySelectorAll('#tab-consoles .console-panel')).map((p) => {
        const b = p.querySelector('.console-monitor-body');
        const r = p.getBoundingClientRect();
        /* La métrica que faltaba: no basta con «tiene líneas», hay que mirar si
           las que caen **dentro de la ventana visible** tienen texto.  Una consola
           llena de líneas en blanco al final se ve negra con el pie en LIVE. */
        let textoEnVentana = null, vaciasAlFinal = null;
        if (b) {
          const lineas = Array.from(b.querySelectorAll('.console-line'));
          const br = b.getBoundingClientRect();
          const marcador = b.querySelector('.console-vacio');
          textoEnVentana = (marcador ? 1 : 0) + lineas.filter((l) => {
            const lr = l.getBoundingClientRect();
            return lr.bottom > br.top && lr.top < br.bottom && (l.textContent || '').trim().length > 0;
          }).length;
          let n = 0;
          for (let i = lineas.length - 1; i >= 0 && !(lineas[i].textContent || '').trim(); i--) n++;
          vaciasAlFinal = n;
        }
        return {
          servicio: p.dataset.service,
          textoEnVentana, vaciasAlFinal,
          visible: r.bottom > 0 && r.top < window.innerHeight,
          hidratado: p.dataset.hydrated === '1',
          lineas: b ? b.querySelectorAll('.console-line').length : null,
          marcador: b && b.querySelector('.console-vacio') ? 'sí' : 'no',
          cuerpoVacio: b ? b.innerHTML.trim().length === 0 : null,
          pie: (p.querySelector('.console-fresh-') || p.querySelector('[id^="console-fresh-"]') || {}).textContent,
          estado: (p.querySelector('[id^="console-footer-status-"]') || {}).textContent,
        };
      });
      const sinMarcador = filas.filter((f) => f.visible && f.lineas === 0 && f.marcador === 'no');
      const informe = {
        versionInterfazCargada: window.__UI_VERSION || '(desconocida)',
        versionInterfazServidor: (globalData && globalData.ui_version) || '(sin dato)',
        coincide: !window.__UI_VERSION || !globalData || window.__UI_VERSION === globalData.ui_version,
        vigilanciaActiva: !!window.__vigilaPanelesVisibles,
        sseSaludable: consoleWorkspace.sseHealthy !== false,
        paneles: filas.length,
        visibles: filas.filter((f) => f.visible).length,
        visibleSinMarcador: sinMarcador,
        detalle: filas,
      };
      console.table ? console.table(filas) : console.log(filas);
      return informe;
    }

    /** Avisa si la página tiene una copia vieja del JS (versión distinta). */
    function avisarVersionVieja() {
      if (!window.__UI_VERSION || !globalData || !globalData.ui_version) return;
      if (window.__UI_VERSION === globalData.ui_version) return;
      if (document.getElementById('avisoVersionVieja')) return;
      const aviso = document.createElement('div');
      aviso.id = 'avisoVersionVieja';
      aviso.style.cssText = 'position:fixed; left:50%; transform:translateX(-50%); bottom:16px; z-index:9999;'
        + 'background:rgba(245,158,11,0.16); border:1px solid var(--warn); color:var(--text);'
        + 'padding:8px 14px; border-radius:8px; font-size:12px; max-width:80vw;';
      aviso.innerHTML = '⚠️ Tu navegador tiene una <b>versión antigua</b> de la interfaz '
        + `(${escapeHtml(String(window.__UI_VERSION))} frente a ${escapeHtml(String(globalData.ui_version))}). `
        + 'Recarga con <b>Ctrl+Shift+R</b>. '
        + '<a href="javascript:void(0)" onclick="this.parentNode.remove()" style="margin-left:8px;">ocultar</a>';
      document.body.appendChild(aviso);
    }

    /** Editor de secretos: el panel lista lo que necesita y el usuario lo rellena. */
    async function openSecretsModal() {
      if (!ensureDevOrAdminAuth()) return;
      const modal = document.getElementById('secretsModal');
      const body = document.getElementById('secretsBody');
      if (modal) modal.style.display = 'flex';
      if (body) body.innerHTML = '<p style="color:var(--text-muted);">Consultando qué credenciales faltan…</p>';
      try {
        const res = await fetch('/api/secrets');
        const d = await res.json();
        const ruta = document.getElementById('secretsPath');
        if (ruta && d.archivo) ruta.textContent = d.archivo;
        const claves = d.claves || [];
        if (!body) return;
        body.innerHTML = claves.length ? claves.map((c) => `
          <label style="display:flex; flex-direction:column; gap:3px;">
            <span style="font-family:var(--font-mono); font-size:11.5px; color:${c.configurada ? 'var(--ok)' : 'var(--warn)'};"
                  title="${c.configurada ? 'ya tiene valor' : 'falta por configurar'}">
              ${c.configurada ? '✔' : '⚠'} ${escapeHtml(c.ruta)}
            </span>
            <input type="password" class="search-input" data-secret-key="${escapeHtml(c.ruta)}"
                   placeholder="${c.configurada ? '•••••• (guardado) — deja vacío para conservarlo' : 'valor pendiente'}"
                   autocomplete="new-password">
          </label>`).join('') : '<p style="color:var(--ok);">No hay credenciales pendientes para esta instalación.</p>';
      } catch (err) {
        if (body) body.innerHTML = `<p style="color:var(--danger);">${escapeHtml(err.message)}</p>`;
      }
    }

    function closeSecretsModal() {
      const modal = document.getElementById('secretsModal');
      if (modal) modal.style.display = 'none';
    }

    /** Busca los secretos en los .env de los servicios del workspace. */
    async function buscarSecretosEnServicios() {
      const body = document.getElementById('secretsBody');
      if (body) body.innerHTML = '<p style="color:var(--text-muted);">Buscando en los .env de los servicios…</p>';
      try {
        const res = await fetch('/api/secrets/buscar', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ env: 'develop' })
        });
        const d = await res.json();
        const h = d.hallazgos || [];
        window.__secretosHallados = d.valores || {};
        if (!body) return;
        body.innerHTML = `
          <div style="font-size:12px; margin-bottom:6px;">
            Encontrados <b>${h.length}</b> en los servicios${(d.pendientes || []).length ? `; siguen pendientes <b>${(d.pendientes || []).length}</b>` : ''}.
          </div>
          ${h.length ? h.map((x) => `
            <label style="display:flex; align-items:center; gap:8px;">
              <input type="checkbox" checked data-hallado="${escapeHtml(x.clave)}">
              <span style="font-family:var(--font-mono); font-size:11.5px;">${escapeHtml(x.clave)}</span>
              <span style="color:var(--text-muted); font-size:11px;">= ${escapeHtml(x.pista)} · de ${escapeHtml(x.origen)}</span>
            </label>`).join('') + `
          <div style="margin-top:10px; display:flex; gap:8px;">
            <button class="btn btn-sm btn-hero" onclick="usarSecretosHallados()">✅ Usar los marcados</button>
            <button class="btn btn-sm btn-outline" onclick="openSecretsModal()">Volver a la lista</button>
          </div>` : '<p style="color:var(--warn);">No se encontró ninguno en los .env de los servicios.</p>'}
          ${(d.pendientes || []).length ? `<div style="font-size:11px; color:var(--text-muted); margin-top:6px;">Pendientes: ${(d.pendientes || []).map(escapeHtml).join(', ')}</div>` : ''}`;
      } catch (err) {
        if (body) body.innerHTML = `<p style="color:var(--danger);">${escapeHtml(err.message)}</p>`;
      }
    }

    /** Guarda los secretos encontrados que el usuario dejó marcados. */
    async function usarSecretosHallados() {
      const valores = {};
      document.querySelectorAll('#secretsBody [data-hallado]').forEach((c) => {
        if (c.checked) {
          const k = c.getAttribute('data-hallado');
          const v = (window.__secretosHallados || {})[k];
          if (k && v) valores[k] = v;
        }
      });
      if (!Object.keys(valores).length) { showToast('⚠️ No marcaste ninguno.'); return; }
      try {
        const res = await fetch('/api/secrets/guardar', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ valores })
        });
        const data = await res.json().catch(() => ({}));
        showToast(((res.ok && data.success !== false) ? '✅ ' : '⚠️ ') + (data.message || ('HTTP ' + res.status)));
        if (res.ok) openSecretsModal();
      } catch (err) { showToast('⚠️ ' + err.message); }
    }

    async function guardarSecretos() {
      if (!ensureDevOrAdminAuth()) return;
      const valores = {};
      document.querySelectorAll('#secretsBody [data-secret-key]').forEach((i) => {
        const v = (i.value || '').trim();
        if (v) valores[i.getAttribute('data-secret-key')] = v;
      });
      if (!Object.keys(valores).length) {
        showToast('⚠️ No escribiste ningún valor nuevo.');
        return;
      }
      try {
        const res = await fetch('/api/secrets/guardar', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ valores })
        });
        const data = await res.json().catch(() => ({}));
        showToast(((res.ok && data.success !== false) ? '✅ ' : '⚠️ ') + (data.message || ('HTTP ' + res.status)));
        if (res.ok) openSecretsModal();
      } catch (err) {
        showToast('⚠️ ' + err.message);
      }
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      const duration = (msg.includes('❌') || msg.toLowerCase().includes('error')) ? 7500 : 3500;
      setTimeout(() => { t.style.display = 'none'; }, duration);
    }

    function openCommandModal({ title, subtitle, command, status, output }) {
      const modal = document.getElementById('commandResultModal');
      if (!modal) return;
      document.getElementById('cmdResultTitle').innerText = title || 'Ejecución de Comando';
      document.getElementById('cmdResultSubtitle').innerText = subtitle || '';
      document.getElementById('cmdResultCommand').innerText = command || '-';
      document.getElementById('cmdResultTimestamp').innerText = new Date().toLocaleTimeString();

      updateCommandModalStatus(status || 'running', output || '');
      modal.style.display = 'flex';
    }

    function updateCommandModalStatus(status, output) {
      const badge = document.getElementById('cmdResultBadge');
      const outBox = document.getElementById('cmdResultOutput');
      const icon = document.getElementById('cmdResultIcon');
      const closeBtn = document.getElementById('btnCmdResultClose');

      outBox.innerText = output || '(Sin salida del proceso)';
      outBox.classList.remove('is-error', 'is-success');

      if (status === 'running') {
        icon.innerText = '⚙️';
        badge.className = 'status-badge';
        badge.style.background = 'rgba(245, 158, 11, 0.15)';
        badge.style.color = '#f59e0b';
        badge.style.border = '1px solid rgba(245, 158, 11, 0.4)';
        badge.innerHTML = '<span class="spinner" style="width:11px; height:11px; border-width:2px; display:inline-block;"></span> EN PROCESO';
        closeBtn.innerText = 'Cerrar';
      } else if (status === 'error') {
        icon.innerText = '❌';
        badge.className = 'status-badge';
        badge.style.background = 'rgba(239, 68, 68, 0.15)';
        badge.style.color = '#ef4444';
        badge.style.border = '1px solid rgba(239, 68, 68, 0.4)';
        badge.innerHTML = '<span class="dot" style="background:#ef4444;"></span> ERROR';
        outBox.classList.add('is-error');
        closeBtn.innerText = 'Entendido / Cerrar';
      } else { // 'success'
        icon.innerText = '✅';
        badge.className = 'status-badge';
        badge.style.background = 'rgba(16, 185, 129, 0.15)';
        badge.style.color = '#10b981';
        badge.style.border = '1px solid rgba(16, 185, 129, 0.4)';
        badge.innerHTML = '<span class="dot" style="background:#10b981;"></span> COMPLETADO';
        outBox.classList.add('is-success');
        closeBtn.innerText = 'Listo';
      }
    }

    function closeCommandModal() {
      const modal = document.getElementById('commandResultModal');
      if (modal) modal.style.display = 'none';
    }

    function copyCommandOutput() {
      const text = document.getElementById('cmdResultOutput').innerText;
      if (!text) {
        showToast('No hay salida para copiar.');
        return;
      }
      navigator.clipboard.writeText(text).then(() => {
        showToast('Salida copiada al portapapeles.');
      });
    }

    function switchTab(tabId, elem) {
      document.querySelectorAll('.tab-link, .sidebar-nav-item').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      const targetPane = document.getElementById('tab-' + tabId);
      if (targetPane) targetPane.classList.add('active');

      // Activar tanto el tab-link como el sidebar-nav-item correspondiente
      document.querySelectorAll(`[data-tab="${tabId}"]`).forEach(btn => btn.classList.add('active'));

      // Cerrar sidebar en pantallas pequeñas
      if (window.innerWidth <= 1024) {
        document.getElementById('sidebarNav')?.classList.remove('mobile-open');
        document.getElementById('sidebarOverlay')?.classList.remove('active');
      }

      if (tabId === 'workspace') fetchWorkspaceStatus();
      if (tabId === 'site' && typeof loadSiteConfig === 'function') loadSiteConfig();
      /* La rejilla de microservicios se reconstruye entera; si su pestaña no está
         visible el trabajo es invisible (medido: ~35 ms cada 3 s con el muro
         delante).  Por eso `renderAllServices()` no pinta fuera de su pestaña y
         aquí se fuerza al entrar. */
      if (tabId === 'services' && typeof renderAllServices === 'function') renderAllServices();
      if (tabId === 'consoles') {
        if (typeof onConsoleTabActivated === 'function') onConsoleTabActivated();
      } else {
        if (typeof onConsoleTabDeactivated === 'function') onConsoleTabDeactivated();
      }
      if (tabId === 'k8s') {
        const tbody = document.getElementById('k8sTableBody');
        if (tbody && (!k8sPodsCache || k8sPodsCache.length === 0)) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:28px; color:var(--text-muted);"><span class="dot pulse"></span> Consultando cluster Kubernetes...</td></tr>`;
        }
        fetchK8sStatus();
        fetchCurrentK8sTheme();
      }
      if (tabId === 'deployments') {
        fetchDeploymentVersions();
        refreshConfigGitStatus();
      }
      if (tabId === 'infra') renderInfraMatrix();
      if (tabId === 'map') fetchOperationalMapData();
      if (tabId === 'activity') fetchLiveActivity();
    }

    function toggleSidebar() {
      const sidebar = document.getElementById('sidebarNav');
      const overlay = document.getElementById('sidebarOverlay');
      if (!sidebar) return;
      if (window.innerWidth <= 1024) {
        sidebar.classList.toggle('mobile-open');
        if (overlay) overlay.classList.toggle('active');
      } else {
        sidebar.classList.toggle('collapsed');
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sisper_sidebar_collapsed', isCollapsed ? 'true' : 'false');
      }
    }

    function openLayoutStudioModal() {
      document.getElementById('layoutStudioModal').style.display = 'flex';
      fetchLayouts();
    }

    function closeLayoutStudioModal() {
      document.getElementById('layoutStudioModal').style.display = 'none';
    }

    // -------------------------------------------------------------------------
    // Selector Dinámico de Directorio Raíz de Proyectos
    // -------------------------------------------------------------------------
    let currentInspectedRootData = null;

    async function openRootFolderModal() {
      if (!ensureDevOrAdminAuth(() => {})) return;

      const modal = document.getElementById('rootFolderModal');
      const input = document.getElementById('inputRootFolder');
      const btnDefault = document.getElementById('btnDefaultRoot');
      const btnApply = document.getElementById('btnApplyRootFolder');
      const statusMsg = document.getElementById('rootFolderStatusMsg');
      if (statusMsg) statusMsg.innerText = '';
      if (btnApply) {
        btnApply.disabled = true;
        btnApply.innerText = '💾 Aplicar y Escanear Proyectos';
      }

      try {
        const res = await fetch('/api/root_dir/info');
        if (res.ok) {
          const info = await res.json();
          currentInspectedRootData = info;
          if (input) input.value = info.path;
          if (btnDefault) {
            btnDefault.dataset.path = info.dashboard_dir;
            btnDefault.innerText = `🏠 Develop (${info.folder_name || 'Develop'})`;
          }
          renderRootFolderPreview(info);
        }
      } catch (err) {
        console.error("Error obteniendo info de raíz:", err);
      }

      modal.style.display = 'flex';
    }

    function closeRootFolderModal() {
      const modal = document.getElementById('rootFolderModal');
      if (modal) modal.style.display = 'none';
      currentInspectedRootData = null;
    }

    async function inspectRootFolder(targetPath = null) {
      const input = document.getElementById('inputRootFolder');
      const path = (targetPath !== null ? targetPath : (input ? input.value : '')).trim();
      if (!path) return;

      if (input && targetPath !== null) input.value = path;

      const loading = document.getElementById('rootFolderPreviewLoading');
      const content = document.getElementById('rootFolderPreviewContent');
      const btnApply = document.getElementById('btnApplyRootFolder');
      const statusMsg = document.getElementById('rootFolderStatusMsg');

      if (loading) loading.style.display = 'block';
      if (content) content.innerHTML = '';
      if (btnApply) btnApply.disabled = true;
      if (statusMsg) statusMsg.innerText = 'Consultando sistema de archivos...';

      try {
        const res = await fetch(`/api/root_dir/inspect?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        currentInspectedRootData = data;
        renderRootFolderPreview(data);
      } catch (err) {
        if (loading) loading.style.display = 'none';
        if (content) content.innerHTML = `<div style="color:var(--danger); font-size:12px;">❌ Error de red: ${err.message}</div>`;
        if (btnApply) btnApply.disabled = true;
        if (statusMsg) statusMsg.innerText = 'Error al inspeccionar.';
      }
    }

    function renderRootFolderPreview(data) {
      const loading = document.getElementById('rootFolderPreviewLoading');
      const content = document.getElementById('rootFolderPreviewContent');
      const btnApply = document.getElementById('btnApplyRootFolder');
      const subdirsList = document.getElementById('rootFolderSubdirsList');
      const subdirsCount = document.getElementById('rootFolderSubdirsCount');
      const statusMsg = document.getElementById('rootFolderStatusMsg');

      if (loading) loading.style.display = 'none';

      if (!data.valid) {
        content.innerHTML = `
          <div style="display:flex; align-items:flex-start; gap:10px; color:#f87171;">
            <div style="font-size:18px;">⚠️</div>
            <div>
              <div style="font-weight:700; font-size:12.5px;">Directorio Inválido o Inaccesible</div>
              <div style="font-size:11.5px; color:#cbd5e1; margin-top:2px;">${data.error || 'La ruta especificada no existe o no tiene permisos de lectura.'}</div>
            </div>
          </div>
        `;
        if (btnApply) btnApply.disabled = true;
        if (statusMsg) statusMsg.innerText = '❌ Selecciona una ruta válida.';
        if (subdirsList) subdirsList.innerHTML = '<span style="color:var(--text-muted); font-size:11px; padding:4px;">No disponible</span>';
        if (subdirsCount) subdirsCount.innerText = '0';
        return;
      }

      const bCount = data.backend_count || 0;
      const fCount = data.frontend_count || 0;
      const hasConfig = data.has_config_json;

      let badgesHtml = '';
      if (bCount > 0) {
        badgesHtml += `<span style="background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid rgba(34,197,94,0.3); padding:3px 8px; border-radius:6px; font-weight:700; font-size:11px;">📦 ${bCount} Backend (${data.has_backend_dir ? 'backend/' : ''})</span> `;
      } else {
        badgesHtml += `<span style="background:rgba(234,179,8,0.15); color:#fde047; border:1px solid rgba(234,179,8,0.3); padding:3px 8px; border-radius:6px; font-size:11px;">⚠️ 0 Backend</span> `;
      }

      if (fCount > 0) {
        badgesHtml += `<span style="background:rgba(56,189,248,0.15); color:#7dd3fc; border:1px solid rgba(56,189,248,0.3); padding:3px 8px; border-radius:6px; font-weight:700; font-size:11px;">🎨 ${fCount} Frontend (${data.has_frontend_dir ? 'frontend/' : ''})</span> `;
      } else {
        badgesHtml += `<span style="background:rgba(234,179,8,0.15); color:#fde047; border:1px solid rgba(234,179,8,0.3); padding:3px 8px; border-radius:6px; font-size:11px;">⚠️ 0 Frontend</span> `;
      }

      if (hasConfig) {
        badgesHtml += `<span style="background:rgba(148,163,184,0.15); color:#cbd5e1; border:1px solid rgba(148,163,184,0.3); padding:3px 8px; border-radius:6px; font-size:11px;">⚙️ config/services.json</span>`;
      }

      let noteHtml = '';
      if (bCount === 0 && fCount === 0) {
        noteHtml = `<div style="margin-top:8px; font-size:11px; color:#fbbf24;">⚠️ Esta carpeta no contiene submódulos 'ms_*' o 'mf_*'. Si continúas, la consola mostrará la lista vacía hasta clonar proyectos.</div>`;
      } else {
        noteHtml = `<div style="margin-top:6px; font-size:11px; color:#94a3b8;">✅ Estructura compatible detectada lista para desplegar y monitorear.</div>`;
      }

      content.innerHTML = `
        <div>
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <div style="font-weight:700; font-size:12.5px; color:#f1f5f9; display:flex; align-items:center; gap:6px;">
              <span>📁 ${data.folder_name}/</span>
              <span style="font-size:10px; color:#64748b; font-family:ui-monospace, monospace;">${data.path}</span>
            </div>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
            ${badgesHtml}
          </div>
          ${noteHtml}
        </div>
      `;

      if (btnApply) btnApply.disabled = false;
      if (statusMsg) statusMsg.innerText = `Listo para aplicar (${bCount + fCount} proyectos detectados).`;

      // Render subdirectorios para navegación rápida
      if (subdirsList) {
        const subdirs = data.subdirs || [];
        if (subdirsCount) subdirsCount.innerText = subdirs.length;
        if (subdirs.length === 0) {
          subdirsList.innerHTML = '<span style="color:var(--text-muted); font-size:11px; padding:4px;">No hay subcarpetas visibles en este nivel.</span>';
        } else {
          subdirsList.innerHTML = subdirs.map(s => {
            const isProjectDir = s.name === 'backend' || s.name === 'frontend' || s.name.startsWith('ms_') || s.name.startsWith('mf_');
            const style = isProjectDir ? 'border-color:rgba(56,189,248,0.4); color:#38bdf8;' : '';
            return `<button type="button" class="btn btn-xs btn-outline" style="font-size:10.5px; padding:3px 8px; ${style}" onclick="setAndInspectFolder('${s.path.replace(/'/g, "\\'")}')">📁 ${s.name}</button>`;
          }).join('');
        }
      }
    }

    function setAndInspectFolder(path) {
      if (!path) return;
      const input = document.getElementById('inputRootFolder');
      if (input) input.value = path;
      inspectRootFolder(path);
    }

    function navigateParentFolder() {
      if (currentInspectedRootData && currentInspectedRootData.parent_dir) {
        setAndInspectFolder(currentInspectedRootData.parent_dir);
      }
    }

    async function applyRootFolder() {
      if (!ensureDevOrAdminAuth(() => {})) return;
      const input = document.getElementById('inputRootFolder');
      const path = (input ? input.value : '').trim();
      if (!path) return;

      const btnApply = document.getElementById('btnApplyRootFolder');
      const statusMsg = document.getElementById('rootFolderStatusMsg');
      if (btnApply) {
        btnApply.disabled = true;
        btnApply.innerText = '⏳ Aplicando y escaneando...';
      }

      try {
        const res = await fetch('/api/root_dir/set', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ path: path })
        });
        const data = await res.json();
        if (data.success) {
          const bText = document.getElementById('baseDirPathText');
          const bBtn = document.getElementById('baseDirPathBtn');
          if (bText) bText.innerText = `📁 ${data.folder_name}/`;
          if (bBtn) bBtn.title = `Directorio raíz de proyectos: ${data.base_dir} (Haz clic para cambiar)`;
          
          closeRootFolderModal();
          showToast(`✅ ${data.message} (${data.backend_count} backend, ${data.frontend_count} frontend detectados).`);
          fetchStatus();
        } else {
          showToast(`❌ Error: ${data.message}`);
          if (statusMsg) statusMsg.innerText = `❌ ${data.message}`;
          if (btnApply) {
            btnApply.disabled = false;
            btnApply.innerText = '💾 Aplicar y Escanear Proyectos';
          }
        }
      } catch (err) {
        showToast(`❌ Error de conexión: ${err.message}`);
        if (btnApply) {
          btnApply.disabled = false;
          btnApply.innerText = '💾 Aplicar y Escanear Proyectos';
        }
      }
    }

    // -------------------------------------------------------------------------
    // Polling Principal
    // -------------------------------------------------------------------------
    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        globalData = await res.json();
        /* Si esta página trae una copia vieja del JS frente a la que sirve el
           servidor, se avisa en pantalla (era el caso de «recargo y sigue igual»). */
        try { avisarVersionVieja(); } catch (_) { /* nunca debe romper el sondeo */ }
        
        if (globalData.base_dir) {
          const bText = document.getElementById('baseDirPathText');
          const bBtn = document.getElementById('baseDirPathBtn');
          const folder = globalData.folder_name || (globalData.base_dir.replace(/\\/g, '/').split('/').filter(Boolean).pop()) || 'Develop';
          if (bText) bText.innerText = `📁 ${folder}/`;
          if (bBtn) bBtn.title = `Directorio raíz de proyectos: ${globalData.base_dir} (Haz clic para cambiar)`;
        }

        updateKpiRibbon(globalData);
        renderAllServices();
        renderInfra();
        renderEnvBox();
        renderEnvBadges();
        if (typeof onServicesUpdatedForConsoleWorkspace === 'function') {
          onServicesUpdatedForConsoleWorkspace();
        }

        if (globalData.env_watcher && Array.isArray(globalData.env_watcher.recent_events)) {
          const envEvents = globalData.env_watcher.recent_events;
          if (lastHandledEnvWatcherTs === null) {
            // Primera lectura tras cargar la página: fijar la línea base en el
            // evento más reciente para no notificar cambios ya ocurridos.
            lastHandledEnvWatcherTs = envEvents.reduce(
              (max, ev) => Math.max(max, Number(ev.timestamp) || 0), 0
            );
          } else {
            envEvents.forEach(ev => {
              const ts = Number(ev.timestamp) || 0;
              if (ts > lastHandledEnvWatcherTs) {
                lastHandledEnvWatcherTs = ts;
                showToast(`🔄 [Auto-Reload .env] Modificación detectada en ${ev.file} -> Servicio '${ev.service}' (: ${ev.port}) recargado.`);
              }
            });
          }
        }
      } catch (e) {
        console.error("Error polling:", e);
      }
    }

    function renderEnvBox() {
      if (globalData.env) {
        const e = globalData.env;
        const bEnv = document.getElementById('badge-env');
        const isLocal = e.env_mode === 'LOCAL';
        bEnv.textContent = isLocal ? 'MODO LOCAL' : 'MODO INTRANET';
        bEnv.className = 'badge-pill ' + (isLocal ? 'badge-local' : 'badge-intranet');

        const isClean = e.bitacora_status.includes('limpio') || e.bitacora_status.includes('ORIGINAL');
        const bBit = document.getElementById('badge-bitacora');
        bBit.textContent = isClean ? 'ORIGINAL' : 'PARCHE LOCAL';
        bBit.className = 'badge-pill ' + (isClean ? 'badge-clean' : 'badge-warn');

        document.getElementById('env-details').textContent = `BD: ${e.database_host || '—'} | Keycloak: ${e.keycloak_url || '—'}`;
        document.getElementById('bitacora-desc').textContent = `Estado en ms_sesion: ${e.bitacora_status}`;
      }
    }

    function renderInfra() {
      if (globalData.infra) {
        const k = globalData.infra.keydb || {};
        const o = globalData.infra.onlyoffice || {};
        const c = globalData.infra.keycloak || {};
        
        // KeyDB
        const isKeyRunning = k.port_open || k.container === 'running';
        const bKey = document.getElementById('badgeKeydb');
        if (bKey) {
          bKey.className = 'status-badge ' + (isKeyRunning ? 'online' : (k.container === 'not_found' ? 'warn' : 'offline'));
          bKey.innerHTML = `<span class="dot"></span> ${isKeyRunning ? 'Activo' : (k.container === 'not_found' ? 'No creado' : 'Apagado')}`;
        }
        const descKey = document.getElementById('descKeydb');
        if (descKey) {
          let descText = `Podman: ${k.container || 'not_found'}`;
          if (k.container === 'not_found') {
            descText = k.image_exists ? 'Podman: No creado (Imagen lista)' : 'Podman: Sin imagen local';
          }
          descKey.innerText = descText;
        }
        const btnsKey = document.getElementById('btnsKeydb');
        if (btnsKey) {
          if (isKeyRunning) {
            btnsKey.innerHTML = `
              <button class="btn btn-sm btn-danger" style="padding:3px 8px;" onclick="infraAction('keydb', 'stop')">⏹️ Detener</button>
              <button class="btn btn-sm btn-outline" style="padding:3px 8px;" onclick="infraAction('keydb', 'restart')">🔄 Reiniciar</button>
            `;
          } else if (k.container === 'not_found') {
            btnsKey.innerHTML = `
              <button class="btn btn-sm ${k.image_exists ? 'btn-primary' : 'btn-warning'}" style="padding:3px 8px;" onclick="infraAction('keydb', 'start')" title="${k.image_exists ? 'Crear contenedor KeyDB (:6379)' : 'Descargar imagen y crear contenedor KeyDB'}">
                ${k.image_exists ? '🚀 Desplegar' : '⬇️ Pullear & Iniciar'}
              </button>
            `;
          } else {
            btnsKey.innerHTML = `<button class="btn btn-sm btn-success" style="padding:3px 8px;" onclick="infraAction('keydb', 'start')">▶️ Iniciar</button>`;
          }
        }

        // OnlyOffice
        const isOnlyRunning = o.port_open || o.container === 'running';
        const bOnly = document.getElementById('badgeOnlyoffice');
        if (bOnly) {
          bOnly.className = 'status-badge ' + (isOnlyRunning ? 'online' : (o.container === 'not_found' ? 'warn' : 'offline'));
          bOnly.innerHTML = `<span class="dot"></span> ${o.port_open ? 'Activo' : (o.container === 'running' ? 'Iniciando...' : (o.container === 'not_found' ? 'No creado' : 'Apagado'))}`;
        }
        const descOnly = document.getElementById('descOnlyoffice');
        if (descOnly) {
          let descText = `Podman: ${o.container || 'not_found'}`;
          if (o.container === 'not_found') {
            descText = o.image_exists ? 'Podman: No creado (Imagen lista)' : 'Podman: Sin imagen local';
          }
          descOnly.innerText = descText;
        }
        const btnsOnly = document.getElementById('btnsOnlyoffice');
        if (btnsOnly) {
          if (isOnlyRunning) {
            btnsOnly.innerHTML = `
              <button class="btn btn-sm btn-danger" style="padding:3px 8px;" onclick="infraAction('onlyoffice-local', 'stop')">⏹️ Detener</button>
              <button class="btn btn-sm btn-outline" style="padding:3px 8px;" onclick="infraAction('onlyoffice-local', 'restart')">🔄 Reiniciar</button>
            `;
          } else if (o.container === 'not_found') {
            btnsOnly.innerHTML = `
              <button class="btn btn-sm ${o.image_exists ? 'btn-primary' : 'btn-warning'}" style="padding:3px 8px;" onclick="infraAction('onlyoffice-local', 'start')" title="${o.image_exists ? 'Crear contenedor OnlyOffice (:8082) con secret y parámetros oficiales' : 'Descargar imagen y desplegar OnlyOffice con configuración oficial'}">
                ${o.image_exists ? '🚀 Desplegar' : '⬇️ Pullear & Iniciar'}
              </button>
            `;
          } else {
            btnsOnly.innerHTML = `<button class="btn btn-sm btn-success" style="padding:3px 8px;" onclick="infraAction('onlyoffice-local', 'start')">▶️ Iniciar</button>`;
          }
        }

        const envEl = document.getElementById('envOnlyofficeContracts');
        if (envEl && o.contracts_env) {
          const ce = o.contracts_env;
          if (ce.synced) {
            envEl.innerHTML = `<span style="color:#34d399; font-weight:600;">✅ .env ms_contratos: IP ${ce.pc_ip} OK (host.containers.internal)</span>`;
          } else {
            envEl.innerHTML = `<span style="color:#fbbf24; font-weight:600;">⚠️ .env ms_contratos: desactualizado</span>
              <button class="btn btn-sm btn-outline" style="padding:1px 6px; font-size:10px; margin-left:4px;" onclick="syncOnlyofficeEnv()" title="Sincronizar variables ONLYOFFICE con tu IP (${ce.pc_ip})">⚙️ Sincronizar IP</button>`;
          }
        }

        // Keycloak
        const isKcRunning = c.port_open || c.container === 'running';
        const bKc = document.getElementById('badgeKeycloak');
        if (bKc) {
          bKc.className = 'status-badge ' + (isKcRunning ? 'online' : 'offline');
          bKc.innerHTML = `<span class="dot"></span> ${c.port_open ? 'Activo' : (c.container === 'running' ? 'Iniciando...' : 'Apagado')}`;
        }
        const descKc = document.getElementById('descKeycloak');
        if (descKc) descKc.innerText = `Docker: ${c.container || 'not_found'}`;
        const btnsKc = document.getElementById('btnsKeycloak');
        if (btnsKc) {
          btnsKc.innerHTML = isKcRunning
            ? `<button class="btn btn-sm btn-danger" style="padding:3px 8px;" onclick="dockerKeycloak('stop')">⏹️ Detener</button>
               <button class="btn btn-sm btn-outline" style="padding:3px 8px;" onclick="dockerKeycloak('restart')">🔄 Reiniciar</button>`
            : `<button class="btn btn-sm btn-success" style="padding:3px 8px;" onclick="dockerKeycloak('start')">▶️ Iniciar</button>`;
        }
      }
    }

    /** Convierte #rrggbb a rgba() para los fondos translúcidos de las insignias. */
    function hexToRgba(hex, alpha) {
      const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());
      if (!match) return `rgba(148, 163, 184, ${alpha})`;
      const n = parseInt(match[1], 16);
      return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
    }

    function renderEnvBadges() {
      const summary = globalData.env_summary || {};
      const counts = summary.aligned_counts || {};
      const total = summary.total_services || 0;
      const envs = summary.environments || {};
      const keys = Object.keys(envs);
      if (!keys.length) return;

      // Las insignias y el selector se construyen desde los entornos
      // configurados: antes eran tres botones y tres <option> fijos en el HTML,
      // con sus tres clases de color, de modo que sólo funcionaban esos tres
      // nombres de entorno.
      const switcher = document.getElementById('globalEnvSwitcher');
      if (switcher) {
        switcher.innerHTML = keys.map(key => {
          const cfg = envs[key] || {};
          const colour = cfg.color || '#94a3b8';
          const label = escapeHtml((cfg.label || key).toUpperCase());
          return `<button class="env-btn" style="background:${hexToRgba(colour, 0.18)}; color:${colour}; border-color:${hexToRgba(colour, 0.45)};"
                    onclick="requestEnvSwitch('${escapeHtml(key)}')"
                    title="${escapeHtml(cfg.description || label)}"
                    data-env="${escapeHtml(key)}">
                    <span style="color:${colour};">●</span> ${label}
                    <span style="opacity:0.7; font-size:10px;">(${counts[key] || 0}/${total})</span>
                  </button>`;
        }).join('');
      }

      const mapSelect = document.getElementById('mapEnvSelect');
      if (mapSelect) {
        const current = mapSelect.value;
        mapSelect.innerHTML = keys.map(key => {
          const label = ((envs[key] || {}).label || key).toUpperCase();
          return `<option value="${escapeHtml(key)}">${escapeHtml(label)}</option>`;
        }).join('');
        if (envs[current]) mapSelect.value = current;
      }
    }

    let filterBehindOnly = false;
    let filterAheadOnly = false;
    let filterDirtyOnly = false;
    let activeKpiFilter = null;
    let currentViewMode = localStorage.getItem('sisper_view_mode') || 'grid';

    function setViewMode(mode) {
      currentViewMode = mode;
      localStorage.setItem('sisper_view_mode', mode);
      const btnG = document.getElementById('btnViewGrid');
      const btnL = document.getElementById('btnViewList');
      if (btnG) btnG.classList.toggle('active', mode === 'grid');
      if (btnL) btnL.classList.toggle('active', mode === 'list');
      renderAllServices();
    }

    function filterKpi(type) {
      if (type === 'k8s') {
        const k8sTabBtn = document.querySelector('[data-tab="k8s"]');
        if (k8sTabBtn) switchTab('k8s', k8sTabBtn);
        return;
      }

      // Asegurar que estamos en la pestaña de microservicios
      const servicesTabBtn = document.querySelector('[data-tab="services"]');
      if (servicesTabBtn && !servicesTabBtn.classList.contains('active')) {
        switchTab('services', servicesTabBtn);
      }

      if (type === 'backend') {
        if (activeKpiFilter === 'backend') {
          activeKpiFilter = null;
        } else {
          activeKpiFilter = 'backend';
          const bTitle = document.querySelector('#tab-services .section-title');
          if (bTitle) bTitle.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      } else if (type === 'frontend') {
        if (activeKpiFilter === 'frontend') {
          activeKpiFilter = null;
        } else {
          activeKpiFilter = 'frontend';
          const fTitles = document.querySelectorAll('#tab-services .section-title');
          if (fTitles && fTitles.length > 1) fTitles[1].scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      } else if (type === 'behind') {
        filterBehindOnly = !filterBehindOnly;
        if (filterBehindOnly) {
          filterAheadOnly = false;
          filterDirtyOnly = false;
          activeKpiFilter = 'behind';
        } else {
          activeKpiFilter = null;
        }
      } else if (type === 'ahead') {
        filterAheadOnly = !filterAheadOnly;
        if (filterAheadOnly) {
          filterBehindOnly = false;
          filterDirtyOnly = false;
          activeKpiFilter = 'ahead';
        } else {
          activeKpiFilter = null;
        }
      } else if (type === 'dirty') {
        filterDirtyOnly = !filterDirtyOnly;
        if (filterDirtyOnly) {
          filterBehindOnly = false;
          filterAheadOnly = false;
          activeKpiFilter = 'dirty';
        } else {
          activeKpiFilter = null;
        }
      }

      const chipBehind = document.getElementById('chipFilterBehind');
      if (chipBehind) {
        chipBehind.classList.toggle('active', filterBehindOnly);
      }

      updateKpiActiveVisuals();
      renderAllServices();
    }

    function updateKpiActiveVisuals() {
      const elB = document.getElementById('kpiBackendStatus');
      const elF = document.getElementById('kpiFrontendStatus');
      const elBehind = document.getElementById('kpiGitBehindStatus');
      const elAhead = document.getElementById('kpiGitAheadStatus');
      const elDirty = document.getElementById('kpiGitDirtyStatus');

      if (elB) elB.classList.toggle('active', activeKpiFilter === 'backend');
      if (elF) elF.classList.toggle('active', activeKpiFilter === 'frontend');
      if (elBehind) elBehind.classList.toggle('active', filterBehindOnly);
      if (elAhead) elAhead.classList.toggle('active', filterAheadOnly);
      if (elDirty) elDirty.classList.toggle('active', filterDirtyOnly);
    }

    function updateKpiRibbon(data) {
      if (!data) return;
      const bList = data.backend || [];
      const fList = data.frontend || [];
      const all = bList.concat(fList);

      const bOnline = bList.filter(s => s.online).length;
      const fOnline = fList.filter(s => s.online).length;
      const totalBehind = all.filter(s => (s.behind || 0) > 0).length;
      const totalAhead = all.filter(s => (s.ahead || 0) > 0).length;
      const totalDirty = all.filter(s => (s.dirty || 0) > 0).length;

      const elB = document.getElementById('kpiValBackend');
      if (elB) elB.innerText = `${bOnline}/${bList.length}`;
      const dotB = document.getElementById('kpiDotBackend');
      if (dotB) dotB.className = `kpi-dot ${bOnline > 0 ? (bOnline === bList.length ? 'dot-online' : 'dot-warn') : 'dot-offline'}`;

      const elF = document.getElementById('kpiValFrontend');
      if (elF) elF.innerText = `${fOnline}/${fList.length}`;
      const dotF = document.getElementById('kpiDotFrontend');
      if (dotF) dotF.className = `kpi-dot ${fOnline > 0 ? (fOnline === fList.length ? 'dot-online' : 'dot-warn') : 'dot-offline'}`;

      const elBehind = document.getElementById('kpiValBehind');
      if (elBehind) elBehind.innerText = totalBehind;

      const elAhead = document.getElementById('kpiValAhead');
      if (elAhead) elAhead.innerText = totalAhead;

      const elDirty = document.getElementById('kpiValDirty');
      if (elDirty) elDirty.innerText = totalDirty;

      const k8sSel = document.getElementById('k8sNamespaceSelect');
      const ns = k8sSel ? k8sSel.value : 'develop';
      const elK8s = document.getElementById('kpiValK8s');
      if (elK8s) elK8s.innerText = ns;

      const elTime = document.getElementById('kpiValTime');
      if (elTime) {
        const now = new Date();
        elTime.innerText = now.toLocaleTimeString();
      }
      updateKpiActiveVisuals();
    }

    let activeCardMenu = null;

    function toggleCardMenu(event, svcName) {
      event.stopPropagation();
      const menuId = `cardMenu-${svcName}`;
      const menu = document.getElementById(menuId);
      const isAlreadyOpen = menu && menu.classList.contains('show');
      closeAllCardMenus();
      closeAllToolbarDropdowns();
      if (!isAlreadyOpen && menu) {
        menu.classList.add('show');
        activeCardMenu = svcName;
        const parentCard = menu.closest('.svc-card') || menu.closest('.svc-list-row');
        if (parentCard) parentCard.classList.add('menu-active');

        // Orientación inteligente: si sobrepasa el borde inferior de pantalla, abrir hacia arriba
        const rect = menu.getBoundingClientRect();
        if (rect.bottom > (window.innerHeight - 20) && rect.top > 250) {
          menu.classList.add('dropup');
        } else {
          menu.classList.remove('dropup');
        }
      }
    }

    function closeAllCardMenus() {
      document.querySelectorAll('.svc-dropdown-menu.show').forEach(m => {
        m.classList.remove('show');
        m.classList.remove('dropup');
      });
      document.querySelectorAll('.svc-card.menu-active, .svc-list-row.menu-active').forEach(c => {
        c.classList.remove('menu-active');
      });
      activeCardMenu = null;
    }

    function toggleToolbarDropdown(event, menuId) {
      event.stopPropagation();
      const menu = document.getElementById(menuId);
      if (!menu) return;
      const isAlreadyOpen = menu.classList.contains('show');
      closeAllToolbarDropdowns();
      closeAllCardMenus();
      if (!isAlreadyOpen) {
        menu.classList.add('show');
      }
    }

    function closeAllToolbarDropdowns() {
      document.querySelectorAll('.toolbar-dropdown-menu.show').forEach(m => m.classList.remove('show'));
    }

    // -------------------------------------------------------------------------
    // Menú de acciones por fila de la matriz de Despliegues
    // -------------------------------------------------------------------------
    // Antes cada fila mostraba cuatro botones (Build, Desplegar, Rollout, Info):
    // con 31 servicios eso dejaba más de cien botones en pantalla y la columna
    // de acciones terminaba dominando la tabla.  Se conserva la acción principal
    // y el resto pasa a un menú.  El menú se posiciona respecto de la ventana
    // para que no lo recorte el contenedor que tiene el desplazamiento.
    let activeDeployRowMenu = null;

    function closeDeployRowMenu() {
      if (activeDeployRowMenu) {
        activeDeployRowMenu.remove();
        activeDeployRowMenu = null;
      }
    }

    function toggleDeployRowMenu(event, serviceName) {
      event.stopPropagation();
      const alreadyOpen = activeDeployRowMenu
        && activeDeployRowMenu.dataset.service === serviceName;
      closeDeployRowMenu();
      if (alreadyOpen) return;

      const svc = (currentDeploymentList || []).find(s => s.name === serviceName);
      if (!svc) return;
      const tag = svc.yaml_version !== '-'
        ? svc.yaml_version
        : (svc.k8s_version !== '-' ? svc.k8s_version : 'latest');

      const menu = document.createElement('div');
      menu.className = 'row-action-menu';
      menu.dataset.service = serviceName;
      menu.innerHTML = `
        <button type="button" onclick="closeDeployRowMenu(); toggleInlineBuildRow('${serviceName}')">📺 Consola de construcción</button>
        <button type="button" onclick="closeDeployRowMenu(); deploySingleManifest('${serviceName}')">${getTechIcon('kubernetes', 12)} Desplegar manifiesto</button>
        <button type="button" onclick="closeDeployRowMenu(); rolloutRestartSingleDeploy('${svc.k8s_deploy}')">🔄 Rollout restart</button>
        <button type="button" onclick="closeDeployRowMenu(); inspectImageModal('${svc.image_name}', '${tag}')">🏷️ Info de la imagen</button>
      `;
      document.body.appendChild(menu);

      const rect = event.currentTarget.getBoundingClientRect();
      const menuWidth = menu.offsetWidth;
      const menuHeight = menu.offsetHeight;
      let left = rect.right - menuWidth;
      let top = rect.bottom + 4;
      if (left < 8) left = 8;
      if (top + menuHeight > window.innerHeight - 8) {
        top = Math.max(8, rect.top - menuHeight - 4);
      }
      menu.style.left = `${Math.round(left)}px`;
      menu.style.top = `${Math.round(top)}px`;

      activeDeployRowMenu = menu;
    }

    document.addEventListener('click', () => {
      closeAllCardMenus();
      closeAllToolbarDropdowns();
      closeDeployRowMenu();
    });

    // El menú está posicionado respecto de la ventana, así que deja de
    // corresponder a su botón si el contenido se desplaza o cambia el tamaño.
    document.getElementById('mainContent')
      ?.addEventListener('scroll', closeDeployRowMenu, { passive: true });
    window.addEventListener('resize', closeDeployRowMenu);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeDeployRowMenu();
    });

    /**
     * Ejecuta una acción real de ciclo de vida sobre UN servicio y muestra la
     * respuesta del servidor (antes no se revisaba: los fallos pasaban inadvertidos).
     */
    async function accionServicioReal(svc, accion) {
      if (!ensureDevOrAdminAuth()) return;
      const port = getPanelPort(svc) || 0;
      const esParada = accion === 'stop-single';
      showToast(`${esParada ? '⏹ Deteniendo' : '🔄 Reiniciando'} ${svc}…`);
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ action: accion, service: svc, port: port })
        });
        let data = null;
        try { data = await res.json(); } catch (_) { data = null; }
        if (res.ok && data && data.success !== false) {
          showToast(`✅ ${data.message || (esParada ? svc + ' detenido' : svc + ' reiniciado')}`);
          if (typeof fetchStatus === 'function') fetchStatus();
        } else {
          showToast(`❌ ${(data && data.message) || ('HTTP ' + res.status + ' al ' + (esParada ? 'detener' : 'reiniciar') + ' ' + svc)}`);
        }
      } catch (err) {
        showToast(`❌ Error al ${esParada ? 'detener' : 'reiniciar'} ${svc}: ${err.message}`);
      }
    }

    async function handleStartOrRestart(name, port, online) {
      if (!ensureDevOrAdminAuth()) return;
      if (online) {
        restartSingle(name, port);
      } else {
        showToast(`🚀 Abriendo ${name} en Tilix...`);
        try {
          const res = await fetch('/api/tilix/launch_selected', {
            method: 'POST',
            headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ services: [name], env: 'develop', force: true, open_viewer: destinoTilix() })
          });
          let data;
          try {
            data = await res.json();
          } catch (jsonErr) {
            data = { success: res.ok, message: `HTTP ${res.status}: Respuesta del servidor` };
          }
          if (data && data.success) {
            showToast(`✅ ${data.message}`);
          } else {
            showToast(`❌ ${data ? data.message : 'Error al lanzar servicio'}`);
          }
        } catch (err) {
          showToast(`❌ Error: ${err.message}`);
        }
        /* Al lanzar, refrescar ya: así el muro (y la propia pestaña) ven la
           sesión nueva sin esperar al sondeo de 3 s. */
        if (typeof fetchStatus === 'function') fetchStatus();
      }
    }

    function copyServiceEndpoint(svcName, port) {
      closeAllCardMenus();
      const url = `http://localhost:${port}`;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url);
        showToast(`📋 Copiado al portapapeles: ${url}`);
      } else {
        showToast(`URL: ${url}`);
      }
    }

    // -------------------------------------------------------------------------
    // Selección Múltiple de Servicios para Lanzamiento Parcial
    // -------------------------------------------------------------------------
    const selectedServices = new Set();

    function toggleServiceSelection(svcName, isChecked) {
      if (isChecked) {
        selectedServices.add(svcName);
      } else {
        selectedServices.delete(svcName);
      }
      updateSelectionUI();
    }

    function selectAllServices(select = true) {
      const all = (globalData.backend || []).concat(globalData.frontend || []);
      if (select) {
        all.forEach(s => selectedServices.add(s.name));
      } else {
        selectedServices.clear();
      }
      updateSelectionUI();
    }

    function toggleSelectAllVisible() {
      const visibleCbs = document.querySelectorAll('.svc-cb');
      const allChecked = Array.from(visibleCbs).every(cb => cb.checked);
      visibleCbs.forEach(cb => {
        const name = cb.dataset.name;
        if (name) {
          if (allChecked) selectedServices.delete(name);
          else selectedServices.add(name);
        }
      });
      updateSelectionUI();
    }

    function updateSelectionUI() {
      const count = selectedServices.size;
      const bar = document.getElementById('selectionActionBar');
      const badge = document.getElementById('selectedCountBadge');
      const btnCount = document.getElementById('btnSelectedCount');

      if (badge) badge.innerText = count;
      if (btnCount) btnCount.innerText = count;
      if (bar) bar.style.display = count > 0 ? 'flex' : 'none';

      document.querySelectorAll('.svc-cb').forEach(cb => {
        const name = cb.dataset.name;
        if (name) {
          const isChecked = selectedServices.has(name);
          cb.checked = isChecked;
          const card = cb.closest('.svc-card') || cb.closest('.svc-list-row');
          if (card) card.classList.toggle('is-selected', isChecked);
        }
      });
    }

    async function launchSelectedServicesPrompt(targetEnv = 'develop') {
      if (!ensureDevOrAdminAuth()) return;
      const list = Array.from(selectedServices);
      if (list.length === 0) {
        showToast("⚠️ Marca primero las casillas de los servicios que deseas abrir.");
        return;
      }
      launchWithConflictCheck('selected-services', { services: list, env: targetEnv });
    }

    async function launchAuxiliary(svcName, auxType = 'consumer') {
      if (!ensureDevOrAdminAuth()) return;
      closeAllCardMenus();
      const label = auxType === 'consumer' ? 'RabbitMQ Consumer' : (auxType === 'worker' ? 'Celery Worker' : 'Terminal Pipenv');
      showToast(`🚀 Lanzando ${label} para ${svcName}...`);
      try {
        const res = await fetch('/api/tilix/launch_auxiliary', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ service: svcName, aux_type: auxType, env: 'develop' })
        });
        const data = await res.json();
        if (data.success) {
          showToast(`✅ ${data.message}`);
        } else {
          showToast(`❌ ${data.message}`);
        }
      } catch (err) {
        showToast(`❌ Error: ${err.message}`);
      }
    }

    async function launchSelectedAuxiliary(auxType = 'consumer') {
      if (!ensureDevOrAdminAuth()) return;
      const list = Array.from(selectedServices);
      if (list.length === 0) {
        showToast("⚠️ Marca primero las casillas de los servicios deseados.");
        return;
      }
      const label = auxType === 'consumer' ? 'Consumers' : 'Workers';
      showToast(`🚀 Lanzando ${label} para ${list.length} servicio(s) en Tilix...`);
      try {
        const res = await fetch('/api/tilix/launch_selected_auxiliary', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ services: list, aux_type: auxType, env: 'develop' })
        });
        const data = await res.json();
        if (data.success) {
          showToast(`✅ ${data.message}`);
        } else {
          showToast(`❌ ${data.message}`);
        }
      } catch (err) {
        showToast(`❌ Error: ${err.message}`);
      }
    }

    function createServiceCard(s) {
      const card = document.createElement('div');
      const behindCount = s.behind || 0;
      const aheadCount = s.ahead || 0;
      const dirtyCount = s.dirty || 0;
      const hasUpstream = s.has_upstream !== false;
      const isChecked = selectedServices.has(s.name);
      card.className = `svc-card ${behindCount > 0 ? 'has-behind' : ''} ${isChecked ? 'is-selected' : ''}`;

      const isBackend = s.type === 'backend' || s.name.startsWith('ms_');
      const isFrontend = s.type === 'frontend' || s.name.startsWith('mf_');
      const techIcon = isBackend ? getTechIcon('django', 17) : (isFrontend ? getTechIcon('react', 15) : '');

      const startRestartBtn = s.online
        ? `<button class="btn-card-action btn-card-restart" onclick="handleStartOrRestart('${s.name}', ${s.port}, true)" title="Reiniciar servicio en su consola Tilix">🔄 Reiniciar</button>`
        : `<button class="btn-card-action btn-card-start" onclick="handleStartOrRestart('${s.name}', ${s.port}, false)" title="Lanzar servicio en Tilix">▶ Iniciar</button>`;

      /* Detener desde la propia tarjeta (antes sólo se podía desde el muro o el
         menú de ⋯): termina la sesión del servicio y su consola. */
      const stopBtn = s.online
        ? `<button class="btn-card-action" style="background:rgba(239,68,68,0.15); border-color:var(--danger); color:var(--danger);" onclick="accionServicioReal('${s.name}', 'stop-single')" title="Detener el servicio (termina su sesión y su consola)">⏹ Detener</button>`
        : '';

      card.innerHTML = `
        <div class="svc-top">
          <div class="svc-head">
            <input type="checkbox" class="svc-cb" id="cb-${s.name}" data-name="${s.name}" ${isChecked ? 'checked' : ''} onchange="toggleServiceSelection('${s.name}', this.checked)" title="Seleccionar ${s.name} para abrir en Tilix">
            ${techIcon}
            <span class="svc-title" title="${escapeHtml(s.name)}">${escapeHtml(s.name)}</span>
            <span class="svc-port-badge">:${s.port}</span>
          </div>
        </div>
        <div class="svc-mid">
          <button class="branch-btn" onclick="openBranchPicker('${s.name}', ${s.port})" title="Cambiar rama Git">
            <span style="display:inline-flex; align-items:center; gap:4px;">${getTechIcon('git', 12)} <span>${escapeHtml(s.branch || 'N/A')}</span></span>
          </button>
          <div style="display:flex; align-items:center; gap:5px; flex-wrap:wrap; justify-content:flex-end;">
            <span class="status-badge ${s.online ? 'online' : 'offline'}">
              <span class="dot"></span> ${s.online ? 'Activo' : 'Apagado'}
            </span>
            ${dirtyCount > 0 ? `<span style="font-size:10px; color:var(--warn); font-weight:700;" title="${dirtyCount} archivo(s) modificados sin commitear">● ${dirtyCount}</span>` : ''}
            ${behindCount > 0 ? `<span class="git-badge-behind" title="Rama desactualizada: ${behindCount} commit(s) pendientes de bajar desde GitLab">${getTechIcon('git', 11)} ⬇️ ${behindCount}</span>` : ''}
            ${aheadCount > 0 ? `<span class="git-badge-ahead" title="${aheadCount} commit(s) locales sin subir a GitLab">⬆️ ${aheadCount}</span>` : ''}
            ${!hasUpstream ? `<span class="git-badge-no-upstream" title="Esta rama no tiene repositorio remoto configurado: no se puede bajar ni subir a GitLab">⚠ Sin remoto</span>` : ''}
          </div>
        </div>
        <div class="svc-bottom">
          <span class="svc-type-tag">${isBackend ? 'django' : 'webpack'}</span>
          <div class="svc-action-group">
            ${startRestartBtn}
            ${stopBtn}
            <div class="svc-dropdown">
              <button class="btn-kebab" onclick="toggleCardMenu(event, '${s.name}')" title="Más opciones">⋮</button>
              <div class="svc-dropdown-menu" id="cardMenu-${s.name}">
                <a href="javascript:void(0)" onclick="openDiagnose('${s.name}')" title="Por qué no arranca: .env, entorno de pipenv, dependencias, puerto…">🩺 ¿Por qué no arranca?</a>
                <a href="javascript:void(0)" onclick="openEnvEditorModal('${s.name}', ${s.port})">📝 Editar .env</a>
                <a href="javascript:void(0)" onclick="handleStartOrRestart('${s.name}', ${s.port}, ${s.online})">${s.online ? '🔄 Reiniciar Servicio' : '▶ Iniciar Servicio'}</a>
                <div class="dropdown-divider"></div>
                <a href="javascript:void(0)" onclick="openGitAuthModal('${s.name}', 'pull')" style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
                  <span style="display:flex; align-items:center; gap:6px;">${getTechIcon('git', 14)} <span>Git Pull</span></span>
                  ${behindCount > 0 ? `<span class="git-badge-behind" style="font-size:10px; padding:1px 5px;">⬇️ ${behindCount}</span>` : ''}
                </a>
                <a href="javascript:void(0)" onclick="openGitAuthModal('${s.name}', 'push')" style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
                  <span style="display:flex; align-items:center; gap:6px;">${getTechIcon('git', 14)} <span>Git Push</span></span>
                  ${aheadCount > 0 ? `<span class="git-badge-ahead" style="font-size:10px; padding:1px 5px;">⬆️ ${aheadCount}</span>` : ''}
                </a>
                <div class="dropdown-divider"></div>
                ${(s.has_consumer || s.name.startsWith('ms_')) ? `<a href="javascript:void(0)" onclick="launchAuxiliary('${s.name}', 'consumer')" style="display:flex; align-items:center; gap:6px;">${getTechIcon('rabbitmq', 14)} <span>Lanzar Consumer (RabbitMQ)</span></a>` : ''}
                ${(s.has_worker || s.name.startsWith('ms_')) ? `<a href="javascript:void(0)" onclick="launchAuxiliary('${s.name}', 'worker')" style="display:flex; align-items:center; gap:6px;">${getTechIcon('celery', 14)} <span>Lanzar Worker (Celery)</span></a>` : ''}
                <a href="javascript:void(0)" onclick="openFocusedTerminal('${s.name}')">💻 Terminal Integrada</a>
                <a href="javascript:void(0)" onclick="openServiceMosaicModal('${s.name}', ${s.port})">📋 Ver Logs Recientes (tmux)</a>
                <a href="javascript:void(0)" onclick="openTilixViewer('${s.name}')">🖥️ Abrir en Visor Tilix</a>
                <a href="javascript:void(0)" onclick="openServiceDetail('${s.name}', ${s.port})">ℹ️ Detalles Técnicos</a>

                <a href="javascript:void(0)" onclick="copyServiceEndpoint('${s.name}', ${s.port})">📋 Copiar URL (: ${s.port})</a>
              </div>
            </div>
          </div>
        </div>
      `;
      return card;
    }

    function createServiceListRow(s) {
      const row = document.createElement('div');
      const behindCount = s.behind || 0;
      const aheadCount = s.ahead || 0;
      const dirtyCount = s.dirty || 0;
      const hasUpstream = s.has_upstream !== false;
      const isChecked = selectedServices.has(s.name);
      row.className = `svc-list-row ${behindCount > 0 ? 'has-behind' : ''} ${isChecked ? 'is-selected' : ''}`;

      const isBackend = s.type === 'backend' || s.name.startsWith('ms_');
      const isFrontend = s.type === 'frontend' || s.name.startsWith('mf_');
      const techIcon = isBackend ? getTechIcon('django', 15) : (isFrontend ? getTechIcon('react', 15) : '');

      row.innerHTML = `
        <div class="svc-list-col-name">
          <input type="checkbox" class="svc-cb" id="cb-list-${s.name}" data-name="${s.name}" ${isChecked ? 'checked' : ''} onchange="toggleServiceSelection('${s.name}', this.checked)" title="Seleccionar ${s.name}" style="margin-right:2px;">
          <span class="status-badge ${s.online ? 'online' : 'offline'}" style="padding:2px 6px;">
            <span class="dot"></span>
          </span>
          ${techIcon}
          <span class="svc-title-list" title="${escapeHtml(s.name)}">${escapeHtml(s.name)}</span>
          <span class="svc-port-badge">:${s.port}</span>
        </div>
        <div class="svc-list-col-branch">
          <button class="branch-btn" onclick="openBranchPicker('${s.name}', ${s.port})" style="max-width:130px;" title="Cambiar rama Git">
            <span style="display:inline-flex; align-items:center; gap:4px;">${getTechIcon('git', 12)} <span>${escapeHtml(s.branch || 'N/A')}</span></span>
          </button>
          ${behindCount > 0 ? `<span class="git-badge-behind" title="${behindCount} commit(s) pendientes de bajar">${getTechIcon('git', 11)} ⬇️ ${behindCount}</span>` : ''}
          ${aheadCount > 0 ? `<span class="git-badge-ahead" title="${aheadCount} commit(s) por subir">⬆️ ${aheadCount}</span>` : ''}
          ${dirtyCount > 0 ? `<span style="font-size:10px; color:var(--warn); font-weight:700;" title="${dirtyCount} archivos modificados">● ${dirtyCount}</span>` : ''}
          ${!hasUpstream ? `<span class="git-badge-no-upstream" title="Esta rama no tiene repositorio remoto configurado: no se puede bajar ni subir a GitLab">⚠ Sin remoto</span>` : ''}
        </div>
        <div class="svc-list-col-actions">
          <button class="btn btn-sm btn-outline" style="padding:3px 8px; font-size:11px; color:#38bdf8;" onclick="openEnvEditorModal('${s.name}', ${s.port})" title="Editar archivo .env">📝 .env</button>
          <button class="btn btn-sm ${s.online ? 'btn-outline' : ''}" style="padding:3px 8px; font-size:11px;" onclick="handleStartOrRestart('${s.name}', ${s.port}, ${s.online})" title="${s.online ? 'Reiniciar servicio' : 'Iniciar en Tilix'}">${s.online ? '🔄' : '▶'}</button>
          <div class="svc-dropdown">
            <button class="btn-kebab" style="padding:3px 7px; font-size:12px;" onclick="toggleCardMenu(event, '${s.name}')" title="Más opciones">⋮</button>
            <div class="svc-dropdown-menu" id="cardMenu-${s.name}">
              <a href="javascript:void(0)" onclick="openGitAuthModal('${s.name}', 'pull')" style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
                <span style="display:flex; align-items:center; gap:6px;">${getTechIcon('git', 14)} <span>Git Pull</span></span>
                ${behindCount > 0 ? `<span class="git-badge-behind" style="font-size:10px; padding:1px 5px;">⬇️ ${behindCount}</span>` : ''}
              </a>
              <a href="javascript:void(0)" onclick="openGitAuthModal('${s.name}', 'push')" style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
                <span style="display:flex; align-items:center; gap:6px;">${getTechIcon('git', 14)} <span>Git Push</span></span>
                ${aheadCount > 0 ? `<span class="git-badge-ahead" style="font-size:10px; padding:1px 5px;">⬆️ ${aheadCount}</span>` : ''}
              </a>
              <div class="dropdown-divider"></div>
              ${(s.has_consumer || s.name.startsWith('ms_')) ? `<a href="javascript:void(0)" onclick="launchAuxiliary('${s.name}', 'consumer')" style="display:flex; align-items:center; gap:6px;">${getTechIcon('rabbitmq', 14)} <span>Lanzar Consumer (RabbitMQ)</span></a>` : ''}
              ${(s.has_worker || s.name.startsWith('ms_')) ? `<a href="javascript:void(0)" onclick="launchAuxiliary('${s.name}', 'worker')" style="display:flex; align-items:center; gap:6px;">${getTechIcon('celery', 14)} <span>Lanzar Worker (Celery)</span></a>` : ''}
              <a href="javascript:void(0)" onclick="launchAuxiliary('${s.name}', 'shell')" style="display:flex; align-items:center; gap:6px;">${getTechIcon('python', 14)} <span>Abrir Terminal (Pipenv)</span></a>
              <a href="javascript:void(0)" onclick="openFocusedTerminal('${s.name}')">💻 Terminal Integrada</a>
              <a href="javascript:void(0)" onclick="openServiceMosaicModal('${s.name}', ${s.port})">📋 Ver Logs Recientes (tmux)</a>
              <a href="javascript:void(0)" onclick="openTilixViewer('${s.name}')">🖥️ Abrir en Visor Tilix</a>
              <div class="dropdown-divider"></div>
              <a href="javascript:void(0)" onclick="openServiceDetail('${s.name}', ${s.port})">ℹ️ Detalles Técnicos</a>
              <a href="javascript:void(0)" onclick="copyServiceEndpoint('${s.name}', ${s.port})">📋 Copiar URL (: ${s.port})</a>
            </div>
          </div>
        </div>
      `;
      return row;
    }

    function renderAllServices() {
      /* Sin su pestaña visible no se pinta: `fetchStatus` corre cada 3 s y la
         rejilla se reconstruye con `innerHTML = ''` (coste medido 35 ms por
         pasada, invisible para el usuario).  Al entrar a la pestaña, `switchTab`
         vuelve a llamar aquí. */
      const servicesPane = document.getElementById('tab-services');
      if (servicesPane && !servicesPane.classList.contains('active')) return;
      if (activeCardMenu || document.querySelector('.svc-dropdown-menu.show')) {
        return;
      }
      const query = (document.getElementById('searchInput').value || '').toLowerCase();
      const bGrid = document.getElementById('backendGrid');
      const fGrid = document.getElementById('frontendGrid');
      bGrid.innerHTML = '';
      fGrid.innerHTML = '';

      if (currentViewMode === 'grid') {
        bGrid.className = 'services-grid';
        fGrid.className = 'services-grid';
      } else {
        bGrid.className = 'services-list-container';
        fGrid.className = 'services-list-container';
      }

      const btnG = document.getElementById('btnViewGrid');
      const btnL = document.getElementById('btnViewList');
      if (btnG) btnG.classList.toggle('active', currentViewMode === 'grid');
      if (btnL) btnL.classList.toggle('active', currentViewMode === 'list');

      let bCount = 0;
      let fCount = 0;

      // Calcular total desactualizados (behind > 0)
      let totalBehind = 0;
      (globalData.backend || []).concat(globalData.frontend || []).forEach(s => {
        if ((s.behind || 0) > 0) totalBehind++;
      });

      const chipBehind = document.getElementById('chipFilterBehind');
      if (chipBehind) {
        if (totalBehind > 0) {
          chipBehind.style.display = 'inline-flex';
          chipBehind.innerText = `⬇️ Desactualizados (${totalBehind})`;
          if (filterBehindOnly) {
            chipBehind.classList.add('active');
          } else {
            chipBehind.classList.remove('active');
          }
        } else {
          chipBehind.style.display = 'none';
          filterBehindOnly = false;
        }
      }

      const isIncludedInSlice = (name) => {
        if (currentSlice === 'all') return true;
        const sliceData = (globalData.slices && globalData.slices[currentSlice]) || {};
        return (sliceData.services_names || []).includes(name);
      };

      const showBackend = activeKpiFilter !== 'frontend';
      const showFrontend = activeKpiFilter !== 'backend';

      if (showBackend) {
        (globalData.backend || []).forEach(s => {
          const matchQ = s.name.toLowerCase().includes(query) || s.port.toString().includes(query);
          const matchBehind = !filterBehindOnly || ((s.behind || 0) > 0);
          const matchAhead = !filterAheadOnly || ((s.ahead || 0) > 0);
          const matchDirty = !filterDirtyOnly || ((s.dirty || 0) > 0);
          if (matchQ && isIncludedInSlice(s.name) && matchBehind && matchAhead && matchDirty) {
            const item = (currentViewMode === 'grid') ? createServiceCard(s) : createServiceListRow(s);
            bGrid.appendChild(item);
            bCount++;
          }
        });
      }

      if (showFrontend) {
        (globalData.frontend || []).forEach(s => {
          const matchQ = s.name.toLowerCase().includes(query) || s.port.toString().includes(query);
          const matchBehind = !filterBehindOnly || ((s.behind || 0) > 0);
          const matchAhead = !filterAheadOnly || ((s.ahead || 0) > 0);
          const matchDirty = !filterDirtyOnly || ((s.dirty || 0) > 0);
          if (matchQ && isIncludedInSlice(s.name) && matchBehind && matchAhead && matchDirty) {
            const item = (currentViewMode === 'grid') ? createServiceCard(s) : createServiceListRow(s);
            fGrid.appendChild(item);
            fCount++;
          }
        });
      }

      document.getElementById('badgeCountBackend').innerText = `${bCount} Servicios`;
      document.getElementById('badgeCountFrontend').innerText = `${fCount} Aplicaciones`;
      updateSelectionUI();
    }

    function toggleBehindFilter(elem) {
      filterBehindOnly = !filterBehindOnly;
      if (filterBehindOnly) {
        filterAheadOnly = false;
        filterDirtyOnly = false;
        activeKpiFilter = 'behind';
        if (elem) elem.classList.add('active');
      } else {
        activeKpiFilter = null;
        if (elem) elem.classList.remove('active');
      }
      updateKpiActiveVisuals();
      renderAllServices();
    }

    async function fetchAllGit() {
      const btn = document.getElementById('btnFetchAllGit');
      const originalHtml = btn ? btn.innerHTML : '🔄 Comprobar GitLab';
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:12px; height:12px; border-width:2px; display:inline-block;"></span> Consultando...';
      }
      showToast('Consultando actualizaciones en GitLab para todos los microservicios...');
      try {
        const res = await fetch('/api/git/fetch_all', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast(`GitLab verificado: ${data.updated}/${data.total} repositorios sincronizados.`);
          await fetchStatus();
        } else {
          showToast('Error al consultar GitLab.', true);
        }
      } catch (err) {
        showToast('Error de red al consultar GitLab.', true);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = originalHtml;
        }
      }
    }

    function filterSlice(key, elem) {
      currentSlice = key;
      document.querySelectorAll('#sliceChips .chip').forEach(c => c.classList.remove('active'));
      elem.classList.add('active');

      const actionRow = document.getElementById('sliceActionRow');
      if (key !== 'all') {
        const sliceData = (globalData.slices && globalData.slices[key]) || {};
        document.getElementById('sliceActionText').innerText = `Flujo: ${sliceData.title || key} (${sliceData.description || ''})`;
        actionRow.style.display = 'flex';
      } else {
        actionRow.style.display = 'none';
      }
      renderAllServices();
    }

    async function launchCurrentSlice() {
      if (!ensureDevOrAdminAuth()) return;
      if (currentSlice === 'all') return;
      showToast(`Lanzando flujo '${currentSlice}' en Tilix...`);
      await fetch('/api/action', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: 'start-slice', slice: currentSlice, open_viewer: destinoTilix() })
      });
      fetchStatus();
    }

    // -------------------------------------------------------------------------
    // Acciones de Servidores e Infraestructura
    // -------------------------------------------------------------------------
    async function runAction(actionName, force = false) {
      const adminActions = ['env-local', 'env-intranet', 'env-local-restart', 'env-intranet-restart', 'bitacora-local', 'bitacora-intranet'];
      if (adminActions.includes(actionName)) {
        if (currentUserRole !== 'admin') {
          ensureAdminAuth(() => runAction(actionName, force), `Cambiar modo de entorno o bitácora (${actionName}) requiere rol Administrador / DevOps.`);
          return;
        }
      }
      if (!ensureDevOrAdminAuth()) return;

      /* Los botones de «Lanzar Tilix» también abren la ventana con las
         consolas: antes sólo creaban las sesiones tmux y parecía que no hacían
         nada (no aparecía ninguna ventana). */
      const abrirVisor = ['b1', 'b2', 'front', 'tabs', 'develop', 'test', 'main', 'single', 'all'].includes(actionName)
        && destinoTilix();
      showToast("Ejecutando: " + actionName + (abrirVisor ? " y abriendo consolas en Tilix…" : ""));
      /* La respuesta NO se puede ignorar: es lo que distingue "hecho" de
         "el backend se negó".  Antes cualquier rechazo (409 por servicios
         activos, 400, 500) se veía igual que un botón muerto. */
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ action: actionName, force: force, open_viewer: abrirVisor })
        });
        const data = await res.json().catch(() => ({}));
        if (res.status === 409 && data.already_running) {
          /* Servicios activos: se ofrece el mismo paso de confirmación que usa
             "Abrir Todo", en vez de dejar la acción a medias. */
          pendingConflictAction = { action: actionName, payload: {} };
          openConflictModal({ count: data.active_count || 0, running: data.active_services || [] });
        } else if (!res.ok || data.success === false) {
          showToast('⚠️ ' + (data.message || `${actionName}: error ${res.status}`));
        } else {
          showToast('✅ ' + (data.message || actionName));
        }
      } catch (err) {
        showToast('⚠️ No se pudo ejecutar ' + actionName + ': ' + err.message);
      }
      fetchStatus();
    }

    // -------------------------------------------------------------------------
    // Comprobación previa (¿puedo lanzar?) y diagnóstico (¿por qué no arranca?)
    // Ambas son de sólo lectura; el arreglo lo ejecuta el usuario.
    // -------------------------------------------------------------------------
    let preflightContinuarCb = null;

    /* Destino de los lanzamientos: ventana de Tilix (como siempre) o sólo las
       consolas del dashboard.  Se recuerda entre sesiones. */
    let launchDestino = localStorage.getItem('sisper_launch_destino') || 'tilix';

    function destinoTilix() { return launchDestino !== 'dashboard'; }

    function pintarDestino() {
      const b = document.getElementById('launchDestinoBtn');
      if (!b) return;
      const tilix = destinoTilix();
      b.innerHTML = tilix ? '🖥️ Destino: Tilix' : '▦ Destino: Dashboard';
      b.style.borderColor = tilix ? '' : 'var(--accent)';
      b.title = tilix
        ? 'Los lanzamientos abren la ventana de Tilix. Clic para abrir sólo las consolas del dashboard.'
        : 'Los lanzamientos abren sólo las consolas del dashboard (sin ventana de Tilix). Clic para volver a Tilix.';
    }

    /** Inicia consolas **sólo en el dashboard**: fija el destino y lanza. */
    async function lanzarSoloDashboard() {
      if (!ensureDevOrAdminAuth()) return;
      launchDestino = 'dashboard';
      localStorage.setItem('sisper_launch_destino', 'dashboard');
      pintarDestino();
      const svcs = Array.from(selectedServices);
      showToast(svcs.length
        ? `▦ Iniciando ${svcs.length} consola(s) en el dashboard (sin ventana de Tilix)…`
        : '▦ Iniciando todas las consolas en el dashboard (sin ventana de Tilix)…');
      if (svcs.length) await launchWithConflictCheck('selected-services', { services: svcs, env: 'develop' });
      else await launchWithConflictCheck('all', {});
    }

    function toggleLaunchDestino() {
      launchDestino = destinoTilix() ? 'dashboard' : 'tilix';
      localStorage.setItem('sisper_launch_destino', launchDestino);
      pintarDestino();
      showToast(destinoTilix()
        ? '🖥️ Los lanzamientos abrirán la ventana de Tilix'
        : '▦ Los lanzamientos abrirán sólo las consolas del dashboard');
    }

    function cerrarSiVacio(html) {
      return html || '<p style="color:var(--text-muted);">Sin incidencias.</p>';
    }

    function pintarHallazgos(lista, color) {
      if (!lista.length) return '';
      return '<ul style="margin:6px 0 0 16px; padding:0;">' + lista.map((h) => `
        <li style="margin-bottom:6px;">
          <b>${h.servicio ? escapeHtml(h.servicio) + ': ' : ''}</b>${escapeHtml(h.mensaje)}
          ${h.comando ? `<div style="margin-top:2px;"><code style="font-size:11px; color:${color};">${escapeHtml(h.comando)}</code></div>` : ''}
        </li>`).join('') + '</ul>';
    }

    async function comprobarAntesDeLanzar(servicios) {
      await runPreflight(servicios || Array.from(selectedServices), null);
    }

    /** Ejecuta el preflight; con `alContinuar` sólo bloquea si hay bloqueantes. */
    async function runPreflight(servicios, alContinuar) {
      let datos = null;
      try {
        const q = (servicios && servicios.length)
          ? ('?services=' + encodeURIComponent(servicios.join(','))) : '';
        const res = await fetch('/api/preflight' + q);
        datos = await res.json();
      } catch (err) {
        /* Si la comprobación falla, no se impide lanzar: sólo se avisa. */
        showToast('⚠️ No se pudo comprobar el entorno: ' + err.message);
        if (alContinuar) alContinuar();
        return;
      }
      if (!datos || (datos.ok && !alContinuar)) { openPreflightModal(datos || {bloqueantes: [], avisos: []}, null); return; }
      if (datos.ok) { if (alContinuar) alContinuar(); return; }
      openPreflightModal(datos, alContinuar);
    }

    function openPreflightModal(d, alContinuar) {
      preflightContinuarCb = alContinuar;
      const body = document.getElementById('preflightBody');
      const btn = document.getElementById('preflightContinueBtn');
      if (btn) btn.textContent = alContinuar ? 'Lanzar igualmente' : 'Cerrar';
      if (body) {
        const bloqueantes = d.bloqueantes || [];
        const avisos = d.avisos || [];
        body.innerHTML = `
          <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:8px;">
            <span class="badge-pill" style="background:rgba(56,189,248,0.14); border:1px solid var(--card-border); font-size:10.5px;">
              Modo ${escapeHtml(d.env_mode || '?')} · ${d.servicios_revisados || 0} servicio(s)
            </span>
            ${bloqueantes.length
              ? `<span class="badge-pill" style="background:rgba(239,68,68,0.18); border:1px solid var(--danger); color:var(--danger); font-size:10.5px;">${bloqueantes.length} bloqueante(s)</span>`
              : '<span class="badge-pill" style="background:rgba(16,185,129,0.18); border:1px solid var(--ok); color:var(--ok); font-size:10.5px;">Sin bloqueantes</span>'}
          </div>
          <div style="font-size:11.5px; color:var(--text-muted);">
            Infra que exige este modo: ${(d.infra_requerida || []).map((x) => `<code>${escapeHtml(x)}</code>`).join(', ') || '—'}
          </div>
          ${bloqueantes.length ? `<h4 style="margin:12px 0 0; color:var(--danger); font-size:13px;">Impiden arrancar</h4>${pintarHallazgos(bloqueantes, 'var(--danger)')}` : ''}
          ${avisos.length ? `<h4 style="margin:12px 0 0; color:var(--warn); font-size:13px;">Avisos</h4>${pintarHallazgos(avisos, 'var(--warn)')}` : ''}
          ${!bloqueantes.length && !avisos.length ? '<p style="color:var(--ok);">Todo listo para lanzar.</p>' : ''}`;
      }
      const modal = document.getElementById('preflightModal');
      if (modal) modal.style.display = 'flex';
    }

    function closePreflightModal() {
      preflightContinuarCb = null;
      const modal = document.getElementById('preflightModal');
      if (modal) modal.style.display = 'none';
    }

    function preflightContinuar() {
      const cb = preflightContinuarCb;
      closePreflightModal();
      if (cb) cb();
    }

    async function openDiagnose(servicio) {
      const modal = document.getElementById('diagnoseModal');
      const body = document.getElementById('diagnoseBody');
      const titulo = document.getElementById('diagnoseTitle');
      if (titulo) titulo.textContent = `🩺 Diagnóstico: ${servicio}`;
      if (body) body.innerHTML = '<p style="color:var(--text-muted);">Analizando…</p>';
      if (modal) modal.style.display = 'flex';
      try {
        const res = await fetch('/api/service/diagnose?service=' + encodeURIComponent(servicio));
        const d = await res.json();
        if (!body) return;
        const colores = { error: 'var(--danger)', aviso: 'var(--warn)', info: 'var(--text-muted)', ok: 'var(--ok)' };
        body.innerHTML = `
          <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
            <span class="badge-pill" style="background:rgba(56,189,248,0.14); border:1px solid var(--card-border); font-size:10.5px;">estado: ${escapeHtml(d.estado || '?')}</span>
            ${d.puerto ? `<span class="badge-pill" style="background:rgba(56,189,248,0.14); border:1px solid var(--card-border); font-size:10.5px;">puerto ${d.puerto}</span>` : ''}
            ${d.venv ? `<span class="badge-pill" style="background:rgba(56,189,248,0.14); border:1px solid var(--card-border); font-size:10.5px;">pipenv: ${escapeHtml(d.venv.split('/').pop())}</span>` : ''}
          </div>
          <div style="font-size:11.5px; color:var(--text-muted); margin-bottom:8px;">
            <code>${escapeHtml(d.repo || '')}</code>${d.lineas_leidas ? ` · ${d.lineas_leidas} líneas de consola revisadas` : ''}
          </div>
          ${(d.hallazgos || []).map((h) => `
            <div style="border-left:3px solid ${colores[h.severidad] || 'var(--card-border)'}; padding:8px 12px; margin-bottom:8px; background:rgba(15,23,42,0.5); border-radius:6px;">
              <div style="font-weight:700; color:${colores[h.severidad] || 'var(--text)'};">${escapeHtml(h.codigo)}</div>
              <div>${escapeHtml(h.mensaje)}</div>
              ${h.comando ? `<div style="margin-top:4px;"><code style="font-size:11.5px; color:var(--accent);">${escapeHtml(h.comando)}</code></div>` : ''}
            </div>`).join('')}`;
      } catch (err) {
        if (body) body.innerHTML = `<p style="color:var(--danger);">${escapeHtml(err.message)}</p>`;
      }
    }

    function closeDiagnoseModal() {
      const modal = document.getElementById('diagnoseModal');
      if (modal) modal.style.display = 'none';
    }

    // -------------------------------------------------------------------------
    // Control de Conflictos de Microservicios Activos
    // -------------------------------------------------------------------------
    let pendingConflictAction = null;

    async function launchWithConflictCheck(actionName, extraPayload = {}) {
      if (!ensureDevOrAdminAuth()) return;
      /* Primero se comprueba que el entorno puede arrancar (infra, .env,
         pipenv, puertos).  Si algo lo impide se avisa y decide el usuario;
         después sigue el flujo de siempre. */
      const servicios = (extraPayload && extraPayload.services) || [];
      await runPreflight(servicios, () => conflictosYLanzar(actionName, extraPayload));
    }

    async function conflictosYLanzar(actionName, extraPayload = {}) {
      try {
        const res = await fetch('/api/services/running');
        if (res.ok) {
          const data = await res.json();
          if (data.count > 0) {
            pendingConflictAction = { action: actionName, payload: extraPayload };
            openConflictModal(data);
            return;
          }
        }
      } catch (e) {
        console.error("Error comprobando servicios en ejecución:", e);
      }
      executeLaunchAction(actionName, extraPayload, false);
    }

    function openConflictModal(runningData) {
      const modal = document.getElementById('conflictLaunchModal');
      const body = document.getElementById('conflictModalBody');
      const count = runningData.count;
      const list = runningData.running || [];
      
      const sample = list.slice(0, 10).map(s => `<li><code>${s.name}</code> (puerto :${s.port}, PIDs: ${s.pids.join(',') || '?'})</li>`).join('');
      const more = list.length > 10 ? `<li><em>...y ${list.length - 10} más</em></li>` : '';
      
      body.innerHTML = `
        <p>Se detectaron <strong>${count}</strong> microservicios activos en puertos del sistema.</p>
        <p>Si abres una nueva sesión o ventana de Tilix mientras estos procesos están corriendo, ocurrirán <strong>errores de colisión de puertos (EADDRINUSE)</strong> y una severa degradación de rendimiento.</p>
        <div style="max-height:140px; overflow-y:auto; background:#0f172a; border:1px solid #1e293b; border-radius:6px; padding:8px 12px; margin:10px 0;">
          <ul style="margin:0; padding-left:18px; font-size:11px;">
            ${sample}
            ${more}
          </ul>
        </div>
        <p style="font-size:12px; color:#94a3b8;">¿Qué deseas hacer?</p>
      `;
      modal.style.display = 'flex';
    }

    function closeConflictModal() {
      document.getElementById('conflictLaunchModal').style.display = 'none';
      pendingConflictAction = null;
    }

    async function confirmConflictForceLaunch() {
      if (!pendingConflictAction) return;
      const { action, payload } = pendingConflictAction;
      closeConflictModal();
      showToast(`Forzando apertura de sesión (${action})...`);
      executeLaunchAction(action, payload, true);
    }

    async function confirmStopAndLaunch() {
      if (!pendingConflictAction) return;
      const { action, payload } = pendingConflictAction;
      closeConflictModal();
      showToast("🧹 Deteniendo y limpiando microservicios activos...");
      await fetch('/api/action', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: 'stop-close' })
      });
      showToast("Esperando liberación de puertos...");
      setTimeout(() => {
        executeLaunchAction(action, payload, true);
        fetchStatus();
      }, 1800);
    }

    function executeLaunchAction(actionName, extraPayload = {}, force = false) {
      if (['develop', 'test', 'main'].includes(actionName)) {
        if (selectedServices.size > 0) {
          launchSelectedServicesPrompt(actionName);
          return;
        }
        launchSingleEnvPrompt(actionName);
      } else if (actionName === 'custom-session') {
        showToast(`Lanzando sesión normalizada en ${(extraPayload.env || 'develop').toUpperCase()}...`);
        fetch('/api/tilix/launch', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ session_path: extraPayload.session_path, env: extraPayload.env, force: force,
                                 open_viewer: destinoTilix() })
        });
      } else if (actionName === 'selected-services') {
        const svcs = extraPayload.services || Array.from(selectedServices);
        const env = extraPayload.env || 'develop';
        showToast(destinoTilix()
          ? `🚀 Abriendo ${svcs.length} servicios seleccionados en 1 ventana Tilix (${env.toUpperCase()})...`
          : `🚀 Iniciando ${svcs.length} servicios seleccionados en el dashboard (${env.toUpperCase()})...`);
        fetch('/api/tilix/launch_selected', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ services: svcs, env: env, force: force, open_viewer: destinoTilix() })
        }).then(r => r.json()).then(data => {
          if (data.success) {
            showToast(`✅ ${data.message}`);
          } else {
            showToast(`❌ ${data.message}`);
          }
        }).catch(err => {
          showToast(`❌ Error de conexión: ${err.message}`);
        });
      } else if (actionName === 'all' && selectedServices.size > 0) {
        launchSelectedServicesPrompt('develop');
      } else {
        runAction(actionName, force);
      }
    }

    async function restartSingle(name, port) {
      if (!ensureDevOrAdminAuth()) return;
      showToast(`Reiniciando ${name} (: ${port})...`);
      await fetch('/api/action', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: 'restart-single', service: name, port: port })
      });
    }

    // -------------------------------------------------------------------------
    // Editor de Archivos .env
    // -------------------------------------------------------------------------
    let currentEnvService = null;
    let currentEnvPort = null;

    async function openEnvEditorModal(svcName, port) {
      currentEnvService = svcName;
      currentEnvPort = port;
      const modal = document.getElementById('envEditorModal');
      const title = document.getElementById('envModalSvcName');
      const pathEl = document.getElementById('envModalPath');
      const textarea = document.getElementById('envModalTextarea');
      const loading = document.getElementById('envModalLoading');
      const chkRestart = document.getElementById('envModalRestartChk');

      if (!modal) return;
      modal.style.display = 'flex';
      if (title) title.innerText = svcName;
      if (pathEl) pathEl.innerText = 'Cargando ruta...';
      if (textarea) textarea.value = '';
      if (loading) loading.style.display = 'flex';
      if (chkRestart) chkRestart.checked = true;

      try {
        const res = await fetch(`/api/env/get?service=${encodeURIComponent(svcName)}`);
        const data = await res.json();
        if (loading) loading.style.display = 'none';
        if (!data.success) {
          showToast('❌ ' + (data.error || 'Error al cargar .env'));
          return;
        }
        if (pathEl) {
          pathEl.innerText = `${data.path} ${data.exists ? '' : '(No existe aún - se creará al guardar)'}`;
        }
        if (textarea) {
          textarea.value = data.content || '';
          textarea.focus();
        }
      } catch (err) {
        if (loading) loading.style.display = 'none';
        showToast('❌ Error de conexión al cargar .env: ' + err.message);
      }
    }

    function closeEnvEditorModal() {
      const modal = document.getElementById('envEditorModal');
      if (modal) modal.style.display = 'none';
      currentEnvService = null;
    }

    async function saveEnvEditorModal() {
      if (!currentEnvService) return;
      const textarea = document.getElementById('envModalTextarea');
      const chkRestart = document.getElementById('envModalRestartChk');
      const btnSave = document.getElementById('envModalSaveBtn');
      const content = textarea ? textarea.value : '';
      const doRestart = chkRestart ? chkRestart.checked : true;

      if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerText = '💾 Guardando...';
      }

      try {
        const res = await fetch('/api/env/save', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            service: currentEnvService,
            content: content,
            restart: doRestart
          })
        });
        const data = await res.json();
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.innerText = '💾 Guardar y Aplicar';
        }
        if (data.success) {
          showToast('✅ ' + data.message);
          closeEnvEditorModal();
          fetchStatus();
        } else {
          showToast('❌ ' + (data.message || 'Error al guardar'));
        }
      } catch (err) {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.innerText = '💾 Guardar y Aplicar';
        }
        showToast('❌ Error al guardar: ' + err.message);
      }
    }

    function reloadEnvEditorModal() {
      if (currentEnvService) {
        openEnvEditorModal(currentEnvService, currentEnvPort);
      }
    }

    async function infraAction(container, subaction, forcePull = false) {
      const isInfraAllowed = (container === 'keydb' || container === 'onlyoffice-local');
      if (!isInfraAllowed && currentUserRole !== 'admin') {
        ensureAdminAuth(() => infraAction(container, subaction, forcePull), `Control de contenedores (${container}) requiere rol Administrador / DevOps.`);
        return;
      }

      const label = (container === 'onlyoffice-local') ? 'OnlyOffice (:8082)' : (container === 'keydb' ? 'KeyDB (:6379)' : container);
      showToast(`Podman: procesando ${subaction} sobre ${label}...`);

      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            action: 'podman-container',
            container: container,
            subaction: subaction,
            force_pull: forcePull
          })
        });
        const data = await res.json();

        if (data.needs_pull) {
          const ok = confirm(`⚠️ Imagen institucional no encontrada en el equipo local:

${data.message}

¿Deseas descargarla ahora desde el Registry y desplegar ${label}? (Esto puede tardar unos minutos)`);
          if (ok) {
            showToast(`Descargando imagen y desplegando ${label}... por favor espera.`);
            infraAction(container, 'start', true);
            return;
          }
        } else {
          showToast(data.message || `${label}: orden completada.`);
        }
      } catch (err) {
        showToast(`Error al procesar acción sobre ${label}: ${err.message}`);
      }

      fetchStatus();
      setTimeout(fetchStatus, 1200);
      setTimeout(fetchStatus, 3000);
      setTimeout(fetchStatus, 6000);
    }

    async function syncOnlyofficeEnv() {
      showToast("Sincronizando variables ONLYOFFICE en ms_sisper_contratos/.env...");
      try {
        const res = await fetch('/api/onlyoffice/sync_env', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({})
        });
        const data = await res.json();
        showToast(data.message || "Variables ONLYOFFICE sincronizadas con tu IP.");
        fetchStatus();
      } catch (e) {
        showToast("Error al sincronizar .env: " + e.message);
      }
    }

    async function dockerKeycloak(subaction) {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => dockerKeycloak(subaction), `Control de Keycloak (${subaction}) requiere rol Administrador / DevOps.`);
        return;
      }
      showToast(`Docker: ${subaction} sobre Keycloak...`);
      await fetch('/api/action', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: 'docker-keycloak', subaction: subaction })
      });
      fetchStatus();
      setTimeout(fetchStatus, 1200);
      setTimeout(fetchStatus, 3000);
      setTimeout(fetchStatus, 6000);
    }

    // -------------------------------------------------------------------------
    // Lanzador de Entorno con Comprobación de Ramas
    // -------------------------------------------------------------------------
    function launchSingleEnvPrompt(targetEnv) {
      pendingEnvTarget = targetEnv;
      const envSummary = globalData.env_summary || {};
      const alignedCounts = envSummary.aligned_counts || {};
      const total = envSummary.total_services || 27;
      const count = alignedCounts[targetEnv] || 0;

      document.getElementById('envLaunchModalTitle').innerText = `Lanzar Sesión: ${targetEnv.toUpperCase()}`;

      if (count < total) {
        document.getElementById('envLaunchModalBody').innerHTML = `
          <p>Actualmente solo <strong>${count}/${total}</strong> microservicios están en la rama <code>${targetEnv}</code>.</p>
          <p>Para que la sesión de Tilix ejecute realmente el código de <strong>${targetEnv.toUpperCase()}</strong>, se recomienda alinear los repositorios limpios antes de abrir las terminales.</p>
          <p style="font-size:11px; color:var(--warn);">⚠️ Nota: Los repositorios con cambios sin commitear serán protegidos y no se modificarán.</p>
        `;
        document.getElementById('btnAlignAndLaunch').style.display = 'inline-flex';
        document.getElementById('btnLaunchCurrentOnly').style.display = 'inline-flex';
      } else {
        document.getElementById('envLaunchModalBody').innerHTML = `
          <p>Todos los <strong>${total}</strong> microservicios ya están alineados en la rama <code>${targetEnv}</code>.</p>
          <p>Se abrirá la sesión de Tilix en 1 sola ventana con 25 paneles configurados para <strong>${targetEnv.toUpperCase()}</strong>.</p>
        `;
        document.getElementById('btnAlignAndLaunch').style.display = 'none';
        document.getElementById('btnLaunchCurrentOnly').innerText = "Abrir Tilix Ahora";
      }

      document.getElementById('envLaunchModal').style.display = 'flex';
    }

    function closeEnvLaunchModal() { document.getElementById('envLaunchModal').style.display = 'none'; }

    async function executeTilixOnly() {
      closeEnvLaunchModal();
      showToast(`Lanzando Tilix en ${pendingEnvTarget.toUpperCase()}...`);
      /* Con credenciales (sin ellas la petición se rechaza y no pasa nada) y
         pidiendo la ventana: es lo que promete el botón. */
      const res = await fetch('/api/action', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: pendingEnvTarget, open_viewer: destinoTilix() })
      });
      const data = await res.json().catch(() => ({}));
      showToast(((res.ok && data.success !== false) ? '✅ ' : '⚠️ ') + (data.message || ('HTTP ' + res.status)));
      fetchStatus();
    }

    async function executeAlignAndLaunch() {
      closeEnvLaunchModal();
      showToast(`Alineando ramas a ${pendingEnvTarget.toUpperCase()}...`);
      await fetch('/api/environment/switch', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ target_env: pendingEnvTarget })
      });
      showToast(`Lanzando Tilix en ${pendingEnvTarget.toUpperCase()}...`);
      const res = await fetch('/api/action', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ action: pendingEnvTarget, open_viewer: true })
      });
      const data = await res.json().catch(() => ({}));
      showToast(((res.ok && data.success !== false) ? '✅ ' : '⚠️ ') + (data.message || ('HTTP ' + res.status)));
      fetchStatus();
    }

    function requestEnvSwitch(targetEnv) {
      launchSingleEnvPrompt(targetEnv);
    }

    // -------------------------------------------------------------------------
    // Layout Studio (Sesiones Tilix)
    // -------------------------------------------------------------------------
    async function fetchLayouts() {
      const res = await fetch('/api/tilix/sessions');
      if (!res.ok) return;
      const data = await res.json();
      const tbody = document.getElementById('layoutsTableBody');
      tbody.innerHTML = '';

      (data.sessions || []).forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${s.name}</strong> ${s.is_default ? '<span style="color:var(--accent); font-size:10px; font-weight:700;">(Predeterminada 25 Paneles)</span>' : ''}</td>
          <td style="font-family:ui-monospace, monospace; color:var(--text-muted);">${s.rel_path}</td>
          <td><span style="font-weight:800; color:#fff;">${s.terminals}</span> terminales</td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-sm btn-dev" onclick="launchCustomSession('${s.abs_path}', 'develop')">🟡 Develop</button>
              <button class="btn btn-sm btn-test" onclick="launchCustomSession('${s.abs_path}', 'test')">🔵 Test</button>
              <button class="btn btn-sm btn-main" onclick="launchCustomSession('${s.abs_path}', 'main')">🟢 Main</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function launchCustomSession(sessionPath, envName) {
      launchWithConflictCheck('custom-session', { session_path: sessionPath, env: envName });
    }

    function openImportModal() {
      const fileInput = document.getElementById('importFileInput');
      if (fileInput) fileInput.value = '';
      document.getElementById('importFileName').value = '';
      document.getElementById('importFileContent').value = '';
      document.getElementById('importDropIcon').innerText = '📁';
      document.getElementById('importDropZoneText').innerText = 'Haz clic aquí para seleccionar un archivo .json';
      document.getElementById('importDropZoneSubtext').innerText = 'o arrastra y suelta el archivo aquí directamente';
      const zone = document.getElementById('importDropZone');
      zone.style.borderColor = '#334155';
      zone.style.background = '#0f172a';
      document.getElementById('importFileStatus').innerText = 'Auto-completado al elegir archivo';
      document.getElementById('importJsonValidation').innerText = 'Sin datos';
      document.getElementById('importJsonValidation').style.color = 'var(--text-muted)';
      document.getElementById('importLayoutModal').style.display = 'flex';
    }

    function closeImportModal() {
      document.getElementById('importLayoutModal').style.display = 'none';
    }

    function handleDragOver(e) {
      e.preventDefault();
      e.stopPropagation();
      const zone = document.getElementById('importDropZone');
      zone.style.borderColor = 'var(--accent)';
      zone.style.background = 'rgba(56, 189, 248, 0.08)';
    }

    function handleDragLeave(e) {
      e.preventDefault();
      e.stopPropagation();
      const zone = document.getElementById('importDropZone');
      zone.style.borderColor = '#334155';
      zone.style.background = '#0f172a';
    }

    function handleDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      const zone = document.getElementById('importDropZone');
      zone.style.borderColor = '#334155';
      zone.style.background = '#0f172a';
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        processLayoutFile(e.dataTransfer.files[0]);
      }
    }

    function onLayoutFileSelected(e) {
      if (e.target.files && e.target.files.length > 0) {
        processLayoutFile(e.target.files[0]);
      }
    }

    function processLayoutFile(file) {
      if (!file) return;
      document.getElementById('importFileName').value = file.name;
      document.getElementById('importDropIcon').innerText = '📄';
      document.getElementById('importDropZoneText').innerText = file.name;
      const sizeKb = (file.size / 1024).toFixed(1);
      document.getElementById('importDropZoneSubtext').innerText = 'Tamaño: ' + sizeKb + ' KB — Listo para importar';
      const zone = document.getElementById('importDropZone');
      zone.style.borderColor = 'var(--accent)';
      zone.style.background = 'rgba(56, 189, 248, 0.05)';
      document.getElementById('importFileStatus').innerText = 'Archivo cargado: ' + file.name;

      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target.result;
        document.getElementById('importFileContent').value = text;
        validateImportJson();
      };
      reader.onerror = () => {
        showToast('Error al leer el archivo seleccionado.');
      };
      reader.readAsText(file);
    }

    function validateImportJson() {
      const text = document.getElementById('importFileContent').value.trim();
      const statusEl = document.getElementById('importJsonValidation');
      if (!text) {
        statusEl.innerText = 'Sin datos';
        statusEl.style.color = 'var(--text-muted)';
        return false;
      }
      try {
        const parsed = JSON.parse(text);
        const textStr = JSON.stringify(parsed);
        const count = (textStr.split('"directory":').length - 1);
        statusEl.innerText = count > 0 ? ('🟢 JSON Válido (~' + count + ' terminales)') : '🟢 JSON Válido';
        statusEl.style.color = 'var(--success)';
        return true;
      } catch (err) {
        statusEl.innerText = '⚠️ JSON Inválido';
        statusEl.style.color = 'var(--warn)';
        return false;
      }
    }

    async function submitImportLayout() {
      let name = document.getElementById('importFileName').value.trim();
      const content = document.getElementById('importFileContent').value.trim();
      if (!name) {
        alert('Por favor selecciona un archivo JSON o ingresa un nombre para guardarlo.');
        return;
      }
      if (!name.endsWith('.json')) {
        name += '.json';
      }
      if (!content) {
        alert('El archivo no contiene texto o el contenido JSON está vacío.');
        return;
      }
      if (!validateImportJson()) {
        if (!confirm('El contenido JSON parece tener errores de sintaxis. ¿Deseas guardarlo de todas formas?')) {
          return;
        }
      }

      showToast('Importando layout ' + name + '...');
      const res = await fetch('/api/tilix/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: name, content: content })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Sesión importada correctamente.");
        closeImportModal();
        fetchLayouts();
      } else {
        alert("Error: " + data.message);
      }
    }

    // -------------------------------------------------------------------------
    // Workspace Environments (Git Sync)
    // -------------------------------------------------------------------------
    async function fetchWorkspaceStatus() {
      const res = await fetch('/api/environment/status');
      if (!res.ok) return;
      const data = await res.json();
      const tbody = document.getElementById('workspaceTableBody');
      tbody.innerHTML = '';

      (data.services || []).forEach(s => {
        const tr = document.createElement('tr');
        const isBackend = s.type === 'backend' || s.name.startsWith('ms_');
        const isFrontend = s.type === 'frontend' || s.name.startsWith('mf_');
        const techIcon = isBackend ? getTechIcon('django', 15) : (isFrontend ? getTechIcon('react', 15) : '');

        tr.innerHTML = `
          <td>
            <div style="display:flex; align-items:center; gap:6px;">
              ${techIcon}
              <strong>${s.name}</strong>
            </div>
          </td>
          <td style="text-transform:uppercase; font-size:10px; color:var(--text-muted); font-weight:700;">${s.type}</td>
          <td><span style="font-family:ui-monospace, monospace; color:var(--accent); font-weight:600; display:inline-flex; align-items:center; gap:4px;">${getTechIcon('git', 12)} <span>${s.branch}</span></span></td>
          <td>
            ${s.branch === 'develop' ? '<span style="color:#facc15; font-weight:700;">● Develop</span>' : 
              s.branch === 'test' ? '<span style="color:#60a5fa; font-weight:700;">● Test</span>' : 
              (s.branch === 'main' || s.branch === 'master') ? '<span style="color:#34d399; font-weight:700;">● Main</span>' : 
              '<span style="color:var(--text-muted);">Feature / Otra</span>'}
            ${(s.behind || 0) > 0 ? `<br><span class="git-badge-behind" style="margin-top:4px;">${getTechIcon('git', 11)} ⬇️ ${s.behind} detrás</span>` : ''}
            ${(s.ahead || 0) > 0 ? `<br><span class="git-badge-ahead" style="margin-top:4px;">⬆️ ${s.ahead} por subir</span>` : ''}
            ${s.has_upstream === false ? `<br><span class="git-badge-no-upstream" style="margin-top:4px;" title="Esta rama no tiene repositorio remoto configurado: no se puede bajar ni subir a GitLab">⚠ Sin remoto</span>` : ''}
          </td>
          <td>
            ${s.dirty > 0 ? `<span style="color:var(--warn); font-weight:800;">⚠️ ${s.dirty} modificados</span>` : '<span style="color:var(--success);">✓ Limpio</span>'}
          </td>
          <td>
            <button class="btn btn-sm btn-outline" onclick="openBranchPicker('${s.name}', ${s.port})">Cambiar Rama</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function switchAllEnv(targetEnv) {
      if (!confirm(`¿Alinear todos los microservicios sin cambios pendientes a la rama '${targetEnv.toUpperCase()}'?`)) return;
      showToast(`Alineando servicios a ${targetEnv.toUpperCase()}...`);
      await fetch('/api/environment/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_env: targetEnv })
      });
      showToast(`Alineación completada para ${targetEnv.toUpperCase()}.`);
      fetchWorkspaceStatus();
      fetchStatus();
    }

    // -------------------------------------------------------------------------
    // Kubernetes (Cluster & Pods) + Logs Pro
    // -------------------------------------------------------------------------
    // -------------------------------------------------------------------------
    // Gestor de Temas Estacionales en K8s (MF_THEME)
    // -------------------------------------------------------------------------
    let currentK8sTheme = 'none';

    /** Entorno vigente para el tema estacional: manda el selector de «Sitio». */
    function siteEntornoVigente() {
      const siteSelect = document.getElementById('siteEnvSelect');
      if (siteSelect && siteSelect.value) return siteSelect.value;
      const nsSelect = document.getElementById('k8sNamespaceSelect');
      return nsSelect ? nsSelect.value : 'develop';
    }

    async function fetchCurrentK8sTheme() {
      const ns = siteEntornoVigente();
      const badge = document.getElementById('k8sThemeCurrentBadge');
      const select = document.getElementById('k8sThemeSelect');

      try {
        const res = await fetch(`/api/k8s/theme?namespace=${encodeURIComponent(ns)}`);
        // Sin esto, un fallo dejaba la insignia en "Consultando tema..." para
        // siempre, que se lee como si siguiera cargando.
        if (!res.ok) {
          if (badge) badge.innerHTML = `🎨 Tema del clúster: <strong style="color:var(--warn);">sin respuesta</strong>`;
          const sb = document.getElementById('k8sThemeSummaryBadge');
          if (sb) sb.innerText = 'sin respuesta';
          return;
        }
        const data = await res.json();
        if (!data.success) {
          if (badge) badge.innerHTML = `🎨 Tema del clúster: <strong style="color:var(--warn);">no disponible</strong>`;
          const sb = document.getElementById('k8sThemeSummaryBadge');
          if (sb) sb.innerText = 'no disponible';
          return;
        }

        currentK8sTheme = data.current_theme || 'none';
        const themeLabelMap = {
          'none': '🏛️ Base Institucional (none)',
          'auto': '📅 Automático (auto)',
          'fiestas-patrias': '🇨🇱 Fiestas Patrias',
          'halloween': '🎃 Halloween',
          'navidad': '🎄 Navidad'
        };
        const lbl = themeLabelMap[currentK8sTheme] || `Tema: ${currentK8sTheme}`;
        if (badge) {
          badge.innerHTML = `🎨 Tema Activo: <strong style="color:#a5f3fc;">${lbl}</strong> (${data.deployment || 'mf-sesion'})`;
        }
        // El bloque está plegado: el resumen debe mostrar el tema vigente sin
        // necesidad de abrirlo.
        const summaryBadge = document.getElementById('k8sThemeSummaryBadge');
        if (summaryBadge) summaryBadge.innerText = lbl;

        if (select) {
          const known = ['none', 'auto', 'fiestas-patrias', 'halloween', 'navidad'];
          if (known.includes(currentK8sTheme)) {
            select.value = currentK8sTheme;
            toggleCustomThemeInput(false);
          } else {
            select.value = '__custom__';
            toggleCustomThemeInput(true);
            const customInp = document.getElementById('k8sThemeCustomInput');
            if (customInp) customInp.value = currentK8sTheme;
          }
        }
      } catch (e) {
        console.error('Error fetching K8s theme:', e);
        if (badge) badge.innerHTML = `🎨 Tema del clúster: <strong style="color:var(--warn);">sin respuesta</strong>`;
      }
    }

    function handleK8sThemeSelectChange(val) {
      if (val === '__custom__') {
        toggleCustomThemeInput(true);
        const customInp = document.getElementById('k8sThemeCustomInput');
        if (customInp) customInp.focus();
      } else {
        toggleCustomThemeInput(false);
      }
    }

    function toggleCustomThemeInput(show) {
      const customInp = document.getElementById('k8sThemeCustomInput');
      if (customInp) customInp.style.display = show ? 'inline-block' : 'none';
    }

    async function applyK8sTheme() {
      const ns = siteEntornoVigente();
      const themeSelect = document.getElementById('k8sThemeSelect');
      const customInp = document.getElementById('k8sThemeCustomInput');
      let chosenTheme = themeSelect ? themeSelect.value : 'none';
      if (chosenTheme === '__custom__') {
        chosenTheme = customInp ? customInp.value.trim() : '';
        if (!chosenTheme) {
          showToast('⚠️ Por favor escribe el identificador del tema personalizado.');
          return;
        }
      }

      showToast(`🚀 Aplicando tema '${chosenTheme}' en namespace '${ns}'...`);
      try {
        const res = await fetch('/api/k8s/theme', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ namespace: ns, theme: chosenTheme })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✅ ' + data.message);
          fetchCurrentK8sTheme();
          if (data.deployment) {
            trackRolloutStatus(data.deployment, ns);
          }
          fetchK8sStatus();
        } else {
          showToast('❌ ' + (data.message || 'Error aplicando tema'));
        }
      } catch (err) {
        showToast('❌ Error: ' + err.message);
      }
    }

    let currentK8sStatusFilter = 'all';
    let k8sPodsCache = [];

    async function fetchK8sStatus() {
      const ns = document.getElementById('k8sNamespaceSelect').value;
      document.getElementById('k8sStatusSubtext').innerText = `Consultando namespace '${ns}'...`;
      const res = await fetch(`/api/k8s/status?namespace=${ns}`);
      if (!res.ok) return;
      const data = await res.json();
      k8sPodsCache = data.pods || [];

      if (!data.online) {
        const tbody = document.getElementById('k8sTableBody');
        // Tres cosas separadas: qué pasó, con qué comando comprobarlo y qué
        // revisar.  Antes se mostraba la excepción cruda de Python.
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:left; padding:20px 24px; color:var(--warn);">
          <div style="font-weight:700; margin-bottom:8px;">⚠️ ${escapeHtml(data.error || 'Cluster no conectado')}</div>
          ${data.detail ? `<div style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted); background:#0b1220; border:1px solid var(--card-border); border-radius:6px; padding:8px 10px; margin-bottom:8px; word-break:break-all;">${escapeHtml(data.detail)}</div>` : ''}
          ${data.hint ? `<div style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(data.hint)}</div>` : ''}
        </td></tr>`;
        document.getElementById('k8sStatusSubtext').innerText = data.error || 'Desconectado';
        return;
      }

      // Helper para detectar pods en proceso de despliegue o transición
      const isPodDeploying = p => {
        const s = (p.status || '').toLowerCase();
        return s.includes('creating') || s.includes('pending') || s.includes('terminating') || s.includes('init:') || s.includes('pulling') || (p.ready && p.ready.startsWith('0/') && !s.includes('error') && !s.includes('crash'));
      };

      // Actualizar contadores de filtros
      const deployingCount = k8sPodsCache.filter(isPodDeploying).length;
      const runningCount = k8sPodsCache.filter(p => p.status === 'Running' && !isPodDeploying(p)).length;
      const errorCount = k8sPodsCache.filter(p => p.status !== 'Running' && !isPodDeploying(p)).length;
      const restartsCount = k8sPodsCache.filter(p => (parseInt(p.restarts, 10) || 0) > 0).length;

      document.getElementById('k8sCountAll').innerText = k8sPodsCache.length;
      document.getElementById('k8sCountRunning').innerText = runningCount;
      const elDeploying = document.getElementById('k8sCountDeploying');
      if (elDeploying) elDeploying.innerText = deployingCount;
      document.getElementById('k8sCountError').innerText = errorCount;
      document.getElementById('k8sCountRestarts').innerText = restartsCount;

      filterK8sPods();
    }

    let k8sAutoRefreshTimer = null;
    function toggleK8sAutoRefresh(enabled) {
      if (k8sAutoRefreshTimer) {
        clearInterval(k8sAutoRefreshTimer);
        k8sAutoRefreshTimer = null;
      }
      if (enabled) {
        k8sAutoRefreshTimer = setInterval(() => {
          const tab = document.getElementById('tab-k8s');
          if (tab && tab.classList.contains('active')) {
            fetchK8sStatus();
          }
        }, 4000);
        showToast("Auto-refresco de Pods K8s activado (cada 4s).");
      }
    }

    function setK8sStatusFilter(filter) {
      currentK8sStatusFilter = filter;
      document.querySelectorAll('.k8s-filter-btn').forEach(btn => btn.classList.remove('active'));
      const activeBtn = document.getElementById(`k8sFilterBtn-${filter}`);
      if (activeBtn) activeBtn.classList.add('active');
      filterK8sPods();
    }

    function clearK8sSearch() {
      const searchInp = document.getElementById('k8sSearchInput');
      if (searchInp) {
        searchInp.value = '';
        filterK8sPods();
      }
    }

    function filterK8sPods() {
      const query = (document.getElementById('k8sSearchInput')?.value || '').trim().toLowerCase();
      const ns = document.getElementById('k8sNamespaceSelect')?.value || 'develop';

      const isPodDeploying = p => {
        const s = (p.status || '').toLowerCase();
        return s.includes('creating') || s.includes('pending') || s.includes('terminating') || s.includes('init:') || s.includes('pulling') || (p.ready && p.ready.startsWith('0/') && !s.includes('error') && !s.includes('crash'));
      };

      let filtered = k8sPodsCache;

      // Filtro por estado
      if (currentK8sStatusFilter === 'Running') {
        filtered = filtered.filter(p => p.status === 'Running' && !isPodDeploying(p));
      } else if (currentK8sStatusFilter === 'deploying') {
        filtered = filtered.filter(isPodDeploying);
      } else if (currentK8sStatusFilter === 'error') {
        filtered = filtered.filter(p => p.status !== 'Running' && !isPodDeploying(p));
      } else if (currentK8sStatusFilter === 'restarts') {
        filtered = filtered.filter(p => (parseInt(p.restarts, 10) || 0) > 0);
      }

      // Filtro por texto de búsqueda
      if (query) {
        filtered = filtered.filter(p => {
          const name = (p.name || '').toLowerCase();
          const ip = (p.ip || '').toLowerCase();
          const status = (p.status || '').toLowerCase();
          return name.includes(query) || ip.includes(query) || status.includes(query);
        });
      }

      renderK8sPodsTable(filtered, ns, query);
    }

    function renderK8sPodsTable(pods, ns, query) {
      const tbody = document.getElementById('k8sTableBody');
      tbody.innerHTML = '';

      if (pods.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:28px;">
          ${query ? `🔍 No se encontraron pods que coincidan con "<strong>${query}</strong>" en namespace '<strong>${ns}</strong>'.` : `No hay pods registrados en el namespace '${ns}'.`}
        </td></tr>`;
        document.getElementById('k8sStatusSubtext').innerText = `0 pods coincidentes de ${k8sPodsCache.length} en namespace '${ns}'.`;
        return;
      }

      document.getElementById('k8sStatusSubtext').innerText = query || currentK8sStatusFilter !== 'all' ? 
        `Mostrando ${pods.length} de ${k8sPodsCache.length} pods en namespace '${ns}'.` : 
        `${k8sPodsCache.length} pods activos en namespace '${ns}'.`;

      // Actualizar Banner Activo de Despliegue en K8s si corresponde
      const banner = document.getElementById('k8sDeployActiveBanner');
      const bannerIcon = document.getElementById('k8sDeployBannerIcon');
      const bannerText = document.getElementById('k8sDeployBannerText');
      if (banner && bannerText) {
        if (currentTrackedDeploy && currentTrackedDeploy.baseName && (!query || query.includes(currentTrackedDeploy.baseName))) {
          banner.style.display = 'flex';
          if (currentTrackedDeploy.status === 'complete') {
            banner.style.borderColor = '#10b981';
            banner.style.background = 'rgba(16, 185, 129, 0.16)';
            bannerIcon.innerText = '✅';
            bannerText.style.color = '#34d399';
            bannerText.innerHTML = `Despliegue finalizado con éxito para: <strong>${currentTrackedDeploy.baseName}</strong> (Pods en Ready 🟢)`;
          } else {
            banner.style.borderColor = '#38bdf8';
            banner.style.background = 'rgba(56, 189, 248, 0.14)';
            bannerIcon.innerText = '🔄';
            bannerText.style.color = '#38bdf8';
            bannerText.innerHTML = `Monitoreando despliegue de: <strong>${currentTrackedDeploy.baseName}</strong> (Inicializando nuevos pods en K8s ⏳)`;
          }
        } else {
          banner.style.display = 'none';
        }
      }

      const isPodDeploying = p => {
        const s = (p.status || '').toLowerCase();
        return s.includes('creating') || s.includes('pending') || s.includes('terminating') || s.includes('init:') || s.includes('pulling') || (p.ready && p.ready.startsWith('0/') && !s.includes('error') && !s.includes('crash'));
      };

      pods.forEach(p => {
        const tr = document.createElement('tr');
        const isDeploying = isPodDeploying(p);
        const isRunning = p.status === 'Running' && !isDeploying;
        const isCrash = p.status.includes('Crash') || p.status.includes('Error') || p.status.includes('BackOff');
        const restartsNum = parseInt(p.restarts, 10) || 0;

        const isTracked = currentTrackedDeploy && currentTrackedDeploy.baseName && p.name.includes(currentTrackedDeploy.baseName);
        const isTrackedDeploying = isTracked && currentTrackedDeploy.status === 'deploying';
        const isTrackedComplete = isTracked && currentTrackedDeploy.status === 'complete';

        let rowStyle = '';
        let deployBadge = '';
        if (isTrackedDeploying) {
          rowStyle = 'background: rgba(56, 189, 248, 0.16); border-left: 5px solid #38bdf8; box-shadow: inset 0 0 16px rgba(56, 189, 248, 0.20); animation: pulseDeployRow 2s infinite;';
          deployBadge = '<span class="badge-pill" style="background:rgba(56,189,248,0.25); color:#38bdf8; border:1px solid #38bdf8; font-size:10px; font-weight:800; padding:1px 6px; margin-left:6px; animation:pulseDeployRow 1.5s infinite;">🚀 DESPLEGANDO</span>';
        } else if (isTrackedComplete) {
          rowStyle = 'background: rgba(16, 185, 129, 0.18); border-left: 5px solid #10b981; box-shadow: inset 0 0 16px rgba(16, 185, 129, 0.22); animation: flashCompleteRow 2.5s ease-out;';
          deployBadge = '<span class="badge-pill" style="background:rgba(16,185,129,0.25); color:#34d399; border:1px solid #10b981; font-size:10px; font-weight:800; padding:1px 6px; margin-left:6px;">✅ DESPLIEGUE OK</span>';
        } else if (isDeploying) {
          rowStyle = 'background: rgba(56, 189, 248, 0.08); border-left: 3px solid #38bdf8;';
          deployBadge = '<span class="badge-pill" style="background:rgba(56,189,248,0.18); color:#38bdf8; border:1px solid rgba(56,189,248,0.4); font-size:9.5px; padding:1px 5px; margin-left:4px;">🔄 EN TRANSICIÓN</span>';
        }
        if (rowStyle) tr.style = rowStyle;

        let badgeHtml = '';
        if (isDeploying) {
          badgeHtml = `
            <span class="status-badge" style="background:rgba(56,189,248,0.2); border:1px solid #38bdf8; color:#38bdf8; font-weight:700;">
              <span class="spinner" style="width:10px; height:10px; border-width:2px; display:inline-block; margin-right:4px;"></span> ${p.status}
            </span>
          `;
        } else if (isRunning) {
          badgeHtml = `
            <span class="status-badge online">
              <span class="dot"></span> ${p.status}
            </span>
          `;
        } else {
          badgeHtml = `
            <span class="status-badge offline" style="${isCrash ? 'background:rgba(239,68,68,0.2); border:1px solid #ef4444; color:#f87171;' : ''}">
              <span class="dot" style="${isCrash ? 'background:#ef4444;' : ''}"></span> ${p.status}
            </span>
          `;
        }

        const pLower = (p.name || '').toLowerCase();
        let podIcon = getTechIcon('kubernetes', 14);
        if (pLower.startsWith('ms-') || pLower.startsWith('ms_')) podIcon = getTechIcon('django', 14);
        else if (pLower.startsWith('mf-') || pLower.startsWith('mf_')) podIcon = getTechIcon('react', 14);
        else if (pLower.includes('keydb') || pLower.includes('redis')) podIcon = getTechIcon('redis', 14);
        else if (pLower.includes('rabbitmq')) podIcon = getTechIcon('rabbitmq', 14);
        else if (pLower.includes('postgres')) podIcon = getTechIcon('postgresql', 14);
        else if (pLower.includes('mongo')) podIcon = getTechIcon('mongodb', 14);
        else if (pLower.includes('keycloak')) podIcon = getTechIcon('keycloak', 14);
        else if (pLower.includes('onlyoffice')) podIcon = getTechIcon('onlyoffice', 14);
        else if (pLower.includes('alfresco')) podIcon = getTechIcon('alfresco', 14);

        tr.innerHTML = `
          <td style="font-family:ui-monospace, monospace; font-weight:700;">
            <div style="display:flex; align-items:center; gap:8px;">
              ${podIcon}
              <span>${p.name}</span>
              ${deployBadge}
            </div>
          </td>
          <td>${badgeHtml}</td>
          <td style="font-weight:700; color:${p.ready && p.ready.startsWith('0/') ? 'var(--warn)' : 'var(--text)'};">${p.ready}</td>
          <td style="color:${restartsNum > 0 ? 'var(--warn)' : 'var(--text-muted)'}; font-weight:700;">${p.restarts}</td>
          <td style="font-family:ui-monospace, monospace; color:var(--text-muted); font-size:11px;">${p.ip}</td>
          <td style="text-align:right;">
            <div style="display:inline-flex; gap:6px; justify-content:flex-end;">
              <button class="btn btn-sm btn-outline" style="padding:3px 8px; font-size:11px;" onclick="openK8sLogs('${p.name}', '${ns}')">📜 Logs Pro</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function openK8sLogs(podName, namespace) {
      const pod = (k8sPodsCache || []).find(x => x.name === podName);
      const containers = pod && pod.containers ? pod.containers : [];

      currentLogTarget = { name: podName, namespace: namespace, rawText: '' };
      document.getElementById('k8sLogsTitle').innerText = podName;
      document.getElementById('k8sLogsNamespaceBadge').innerText = `ns: ${namespace}`;

      const cSelect = document.getElementById('k8sLogsContainerSelect');
      cSelect.innerHTML = '<option value="">(Predeterminado)</option>';
      (containers || []).forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        cSelect.appendChild(opt);
      });

      document.getElementById('k8sLogsModal').style.display = 'flex';
      await refreshCurrentLogs();
    }

    async function refreshCurrentLogs() {
      if (!currentLogTarget.name) return;
      const tail = document.getElementById('k8sLogsTailSelect').value;
      const container = document.getElementById('k8sLogsContainerSelect').value;
      let url = `/api/k8s/logs?target=${currentLogTarget.name}&namespace=${currentLogTarget.namespace}&tail=${tail}`;
      if (container) url += `&container=${container}`;

      document.getElementById('k8sLogsTerminalStatus').innerText = "conectando...";
      const res = await fetch(url);
      const text = await res.text();
      currentLogTarget.rawText = text;
      document.getElementById('k8sLogsTerminalStatus').innerText = "activo (" + new Date().toLocaleTimeString() + ")";
      applyLogFilter();
    }

    let currentLogsFontSize = 12;

    function changeLogsFontSize(delta) {
      currentLogsFontSize = Math.max(9, Math.min(24, currentLogsFontSize + delta));
      const body = document.getElementById('k8sLogsBody');
      if (body) {
        body.style.fontSize = currentLogsFontSize + 'px';
      }
    }

    function toggleMaximizeK8sLogs() {
      const modal = document.querySelector('#k8sLogsModal .modal');
      const btn = document.getElementById('btnMaximizeLogs');
      if (modal) {
        modal.classList.toggle('maximized');
        const isMax = modal.classList.contains('maximized');
        if (btn) btn.innerText = isMax ? '🗗' : '🗖';
      }
    }

    function setLogFilter(term) {
      const input = document.getElementById('k8sLogsFilterInput');
      if (input) {
        input.value = term;
        applyLogFilter();
      }
    }


    function escapeRegex(str) {
      if (!str) return '';
      const specials = ['-', '[', ']', '/', '{', '}', '(', ')', '*', '+', '?', '.', '\\', '^', '$', '|'];
      let res = '';
      for (let i = 0; i < str.length; i++) {
        const c = str[i];
        if (specials.indexOf(c) !== -1) {
          res += String.fromCharCode(92) + c;
        } else {
          res += c;
        }
      }
      return res;
    }

    function applyLogFilter() {
      // Delegates to ConsoleViewport (canonical console renderer, Phase 6S).
      // Behaviour is unchanged: filter by query when present, classify
      // error/warn/info lines, highlight matches, pin to the newest line.
      const q = (document.getElementById('k8sLogsFilterInput').value || '').trim();
      const body = document.getElementById('k8sLogsBody');
      const raw = currentLogTarget.rawText || '';
      const lines = raw.split(String.fromCharCode(10));

      const rendered = ConsoleViewport.renderLines(lines, { query: q, filter: Boolean(q) });

      document.getElementById('k8sLogsLineCount').innerText = `${rendered.count} líneas`;

      if (rendered.count === 0) {
        body.innerHTML = '<div style="color:var(--text-muted); padding:10px;">(Sin logs para el filtro especificado)</div>';
        return;
      }

      body.innerHTML = rendered.html;
      body.scrollTop = body.scrollHeight;
    }

    function toggleAutoLogsRefresh(checkbox) {
      if (checkbox.checked) {
        logAutoInterval = setInterval(refreshCurrentLogs, 3000);
      } else {
        if (logAutoInterval) clearInterval(logAutoInterval);
        logAutoInterval = null;
      }
    }

    function copyLogContent() {
      navigator.clipboard.writeText(currentLogTarget.rawText);
      showToast("Logs copiados al portapapeles.");
    }

    function scrollLogsToBottom() {
      const b = document.getElementById('k8sLogsBody');
      b.scrollTop = b.scrollHeight;
    }

    function closeK8sLogsModal() {
      if (logAutoInterval) clearInterval(logAutoInterval);
      logAutoInterval = null;
      document.getElementById('k8sLogsAutoRefresh').checked = false;
      document.getElementById('k8sLogsModal').style.display = 'none';
      const modal = document.querySelector('#k8sLogsModal .modal');
      if (modal) modal.classList.remove('maximized');
      const btn = document.getElementById('btnMaximizeLogs');
      if (btn) btn.innerText = '🗖';
    }

    let rolloutTrackTimer = null;
    let rolloutTrackStartTime = null;
    let currentTrackedDeploy = null;

    function closeRolloutTracker() {
      if (rolloutTrackTimer) {
        clearInterval(rolloutTrackTimer);
        rolloutTrackTimer = null;
      }
      const el = document.getElementById('rolloutLiveTracker');
      if (el) el.style.display = 'none';
    }

    function goToK8sTab() {
      switchTab('k8s');
      if (currentTrackedDeploy && currentTrackedDeploy.baseName) {
        const ns = currentTrackedDeploy.namespace;
        if (ns) {
          const nsSelect = document.getElementById('k8sNamespaceSelect');
          if (nsSelect && nsSelect.value !== ns) nsSelect.value = ns;
        }
        const searchInp = document.getElementById('k8sSearchInput');
        if (searchInp) {
          searchInp.value = currentTrackedDeploy.baseName;
        }
        setK8sStatusFilter('all');
        fetchK8sStatus();
      } else {
        fetchK8sStatus();
      }
    }

    function clearTrackedDeployFilter() {
      currentTrackedDeploy = null;
      const b = document.getElementById('k8sDeployActiveBanner');
      if (b) b.style.display = 'none';
      const inp = document.getElementById('k8sSearchInput');
      if (inp) inp.value = '';
      filterK8sPods();
    }

    function trackRolloutStatus(deployName, namespace = 'develop') {
      if (!deployName) return;
      const cleanDeploy = deployName.replace(/-[0-9a-f]{7,10}-[a-z0-9]{5}$/, '');
      const targetDeploy = cleanDeploy.endsWith('-deployment') ? cleanDeploy : `${cleanDeploy}-deployment`;
      const baseName = cleanDeploy.replace(/-deployment$/, '');

      currentTrackedDeploy = {
        deploy: targetDeploy,
        baseName: baseName,
        namespace: namespace,
        status: 'deploying'
      };

      const tracker = document.getElementById('rolloutLiveTracker');
      const targetEl = document.getElementById('rolloutTrackerTarget');
      const msgEl = document.getElementById('rolloutTrackerMsg');
      const timeEl = document.getElementById('rolloutTrackerTime');
      const spinnerEl = document.getElementById('rolloutTrackerSpinner');
      const viewBtn = document.getElementById('rolloutTrackerViewBtn');

      if (!tracker || !targetEl || !msgEl) return;

      tracker.style.display = 'block';
      tracker.style.borderColor = '#38bdf8';
      targetEl.innerText = `deployment/${targetDeploy} (${namespace})`;
      msgEl.innerText = 'Consultando estado del rollout en K8s...';
      msgEl.style.color = '#cbd5e1';
      if (spinnerEl) spinnerEl.style.display = 'inline-block';
      if (viewBtn) {
        viewBtn.innerHTML = '🔍 Ver en Pods K8s ➔';
        viewBtn.style.borderColor = '#38bdf8';
        viewBtn.style.color = '#38bdf8';
      }

      if (rolloutTrackTimer) clearInterval(rolloutTrackTimer);
      rolloutTrackStartTime = Date.now();

      const poll = async () => {
        try {
          const elapsedSec = Math.round((Date.now() - rolloutTrackStartTime) / 1000);
          if (timeEl) timeEl.innerText = `Transcurrido: ${elapsedSec}s • ns: ${namespace}`;

          const res = await fetch(`/api/k8s/rollout_status?target=${encodeURIComponent(targetDeploy)}&namespace=${encodeURIComponent(namespace)}&_t=${Date.now()}`);
          if (!res.ok) return;
          const data = await res.json();

          if (data.complete) {
            currentTrackedDeploy.status = 'complete';
            msgEl.innerText = `✅ ${data.message || 'Despliegue completado con éxito. Pods en Ready.'}`;
            msgEl.style.color = '#34d399';
            tracker.style.borderColor = '#10b981';
            if (spinnerEl) spinnerEl.style.display = 'none';
            if (viewBtn) {
              viewBtn.innerHTML = '🟢 Ver Pod Listo en K8s ➔';
              viewBtn.style.borderColor = '#10b981';
              viewBtn.style.color = '#34d399';
            }
            clearInterval(rolloutTrackTimer);
            rolloutTrackTimer = null;
            if (typeof fetchDeploymentVersions === 'function') fetchDeploymentVersions();
            const tabK8s = document.getElementById('tab-k8s');
            if (tabK8s && tabK8s.classList.contains('active')) fetchK8sStatus();
            setTimeout(() => {
              if (!rolloutTrackTimer && tracker.style.display !== 'none') {
                tracker.style.display = 'none';
              }
            }, 8000);
          } else {
            currentTrackedDeploy.status = 'deploying';
            msgEl.innerText = `🔄 ${data.message || 'Esperando que los nuevos pods terminen de inicializar...'}`;
            msgEl.style.color = '#38bdf8';
            tracker.style.borderColor = '#38bdf8';
            if (viewBtn) {
              viewBtn.innerHTML = '🔍 Ver en Pods K8s ➔';
              viewBtn.style.borderColor = '#38bdf8';
              viewBtn.style.color = '#38bdf8';
            }
            const tabK8s = document.getElementById('tab-k8s');
            if (tabK8s && tabK8s.classList.contains('active')) fetchK8sStatus();
          }
        } catch (e) {
          console.error("Rollout track error:", e);
        }
      };

      poll();
      rolloutTrackTimer = setInterval(poll, 2500);
    }

    async function rolloutRestartDeploy(podName, namespace) {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => rolloutRestartDeploy(podName, namespace), `Rollout restart de pods requiere rol Administrador / DevOps.`);
        return;
      }
      const deployName = podName.replace(/-[0-9a-f]{7,10}-[a-z0-9]{5}$/, '');
      showToast(`Reiniciando deployment ${deployName}...`);
      const res = await fetch('/api/k8s/restart', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ deploy: deployName, namespace: namespace })
      });
      const data = await res.json();
      showToast(data.message);
      trackRolloutStatus(deployName, namespace);
      setTimeout(fetchK8sStatus, 1500);
    }

    // -------------------------------------------------------------------------
    // Deployments & Versiones (CI/CD) & Image Builder
    // -------------------------------------------------------------------------
    let currentDeploymentList = [];
    /*: Construcciones simultáneas al construir por selección (cada una es un
       `podman build` + `push`; más de 3 suele saturar la máquina). */
    const MAX_BUILD_PARALELO = 3;
    /* Fuente de verdad de la selección de la tabla de Despliegues.  Antes sólo
       vivía en los checkboxes del DOM, así que cualquier re-render (por ejemplo
       al guardar la versión YAML de un servicio) la borraba. */
    const deploySelection = new Set();
    /* nombre -> {deploy, env} de la última tabla pintada (evita leer el DOM). */
    const deployMetaByName = new Map();
    let currentSingleBuildSvc = null;
    let currentBuildTaskId = null;
    let activeBuildTasks = {};
    let serviceBuildTaskMap = {}; // svcName -> taskId
    let buildPollInterval = null;

    async function fetchDeploymentVersions() {
      const envKey = document.getElementById('deployEnvSelect').value;
      const res = await fetch(`/api/deployments/versions?env=${envKey}`);
      if (!res.ok) return;
      const data = await res.json();
      currentDeploymentList = data.services || [];
      const tbody = document.getElementById('deploymentsTableBody');
      tbody.innerHTML = '';

      deployMetaByName.clear();
      currentDeploymentList.forEach((s) => {
        deployMetaByName.set(s.name, { deploy: s.k8s_deploy, env: envKey });
        const tr = document.createElement('tr');
        tr.id = `deploy-row-${s.name}`;
        tr.innerHTML = `
          <td class="col-chk"><input type="checkbox" class="deploy-chk" data-name="${s.name}" data-deploy="${s.k8s_deploy}" ${deploySelection.has(s.name) ? 'checked' : ''} onchange="onDeploySelectionChange(this)"></td>
          <td class="col-svc">
            <div style="display:flex; flex-direction:column; gap:2px;">
              <div style="display:flex; align-items:center; gap:6px;">
                ${s.name.startsWith('ms_') ? getTechIcon('django', 15) : (s.name.startsWith('mf_') ? getTechIcon('react', 15) : '')}
                <strong>${s.name}</strong>
                <span id="svc-build-badge-${s.name}"></span>
              </div>
              <small style="font-family:ui-monospace, monospace; color:var(--text-muted); font-size:10px;">${s.k8s_deploy}</small>
            </div>
          </td>
          <td class="col-branch">
            <span class="badge-path" style="font-size:10px; font-weight:700; ${s.git_dirty ? 'color:var(--warn);' : ''}">
              <span style="display:inline-flex; align-items:center; gap:4px;">${getTechIcon('git', 12)} <span>${s.current_branch}${s.git_dirty ? ' *' : ''}</span></span>
            </span>
          </td>
          <td class="col-type" style="text-transform:uppercase; font-size:10px; color:var(--text-muted); font-weight:700;">${s.type}</td>
          <td class="col-ver">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-family:ui-monospace, monospace; font-weight:700; color:var(--accent); font-size:12px;">${s.yaml_version}</span>
              <button class="btn btn-sm btn-outline" style="padding:1px 6px;" onclick="openEditYamlVersion('${s.name}', '${s.yaml_version}')" title="Modificar versión en YAML">✏️</button>
            </div>
          </td>
          <td class="col-k8sver"><span style="font-family:ui-monospace, monospace; font-weight:700; font-size:12px;">${s.k8s_version}</span></td>
          <td class="col-status">
            ${s.is_synced ? '<span class="status-badge online"><span class="dot"></span> Sincronizado</span>' : 
              '<span class="status-badge offline"><span class="dot"></span> Diferente</span>'}
          </td>
          <td class="col-actions">
            <div class="deploy-action-btns">
              <button class="btn btn-sm" style="background:#0284c7; color:#fff; padding:3px 8px; font-size:11px; display:inline-flex; align-items:center; gap:4px;" onclick="openSingleBuildModal('${s.name}')" title="Construir imagen local (podman build)">${getTechIcon('podman', 12)} <span>Build</span></button>
              <button id="btn-inline-log-${s.name}" class="btn btn-sm btn-outline" style="display:none; padding:3px 8px; font-size:11px; border-color:#38bdf8; color:#38bdf8;" onclick="toggleInlineBuildRow('${s.name}')" title="Mostrar/Ocultar consola de construcción">📺 Log</button>
              <button class="btn btn-sm btn-outline" style="padding:3px 8px; font-size:13px; line-height:1;" onclick="toggleDeployRowMenu(event, '${s.name}')" title="Más acciones: desplegar, rollout, info de imagen">⋯</button>
            </div>
          </td>
        `;

        const inlineTr = document.createElement('tr');
        inlineTr.id = `deploy-inline-row-${s.name}`;
        inlineTr.className = 'deploy-inline-row';
        inlineTr.style.display = 'none';
        inlineTr.innerHTML = `
          <td colspan="8" style="padding:0; border-top:1px solid #1e293b; border-bottom:2px solid #334155; background:rgba(15, 23, 42, 0.75);">
            <div id="deploy-inline-container-${s.name}" class="deploy-inline-wrapper">
              <div class="deploy-inline-header">
                <div style="display:flex; align-items:center; gap:10px; min-width:0; flex:1;">
                  <span style="font-weight:700; font-size:12px; color:#f8fafc; display:flex; align-items:center; gap:6px; white-space:nowrap;">
                    <span id="inline-status-icon-${s.name}">⚙️</span>
                    <span id="inline-title-${s.name}">Consola: ${s.name}</span>
                  </span>
                  <span id="inline-badge-${s.name}" class="status-badge online" style="font-size:10px; padding:2px 8px; white-space:nowrap;"><span class="dot"></span> EN EJECUCIÓN</span>
                  <span id="inline-step-${s.name}" style="font-size:11px; color:#38bdf8; font-family:ui-monospace, monospace; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Iniciando runner...</span>
                </div>
                
                <div style="display:flex; align-items:center; gap:6px; flex-shrink:0; white-space:nowrap;">
                  <span id="inline-lines-${s.name}" style="font-size:11px; color:#64748b; font-family:ui-monospace, monospace; margin-right:4px;">0 líneas</span>
                  <button class="btn btn-sm btn-outline" style="padding:2px 8px; font-size:11px;" onclick="copyInlineBuildLogs('${s.name}')" title="Copiar logs al portapapeles">📋 Copiar</button>
                  <button class="btn btn-sm btn-outline" id="btn-autoscroll-${s.name}" style="padding:2px 8px; font-size:11px;" onclick="toggleInlineAutoScroll('${s.name}')" title="Alternar auto-scroll">⬇️ Auto-scroll: ON</button>
                  <button class="btn btn-sm btn-outline" id="btn-expand-${s.name}" style="padding:2px 8px; font-size:11px;" onclick="toggleInlineHeight('${s.name}')" title="Expandir/Reducir altura">↕️ Altura</button>
                  <button class="btn btn-sm btn-outline" style="padding:2px 8px; font-size:11px;" onclick="popoutToModal('${s.name}')" title="Abrir en ventana modal flotante">⤢ Modal</button>
                  <button class="btn btn-sm btn-outline" style="padding:2px 8px; font-size:11px;" onclick="collapseInlineBuildRow('${s.name}')" title="Minimizar a la fila">🗕 Minimizar</button>
                  <button class="btn btn-sm btn-outline" style="padding:2px 8px; font-size:11px; color:#ef4444; border-color:rgba(239,68,68,0.3);" onclick="closeInlineBuildRow('${s.name}')" title="Cerrar consola inline">&times;</button>
                </div>
              </div>
              
              <div style="width:100%; height:4px; background:#1e293b; overflow:hidden;">
                <div id="inline-progress-${s.name}" style="width:0%; height:100%; background:var(--accent); transition:width 0.3s ease;"></div>
              </div>
              
              <div id="inline-terminal-${s.name}" class="deploy-inline-body" data-autoscroll="true">Cargando salida del proceso...</div>
            </div>
          </td>
        `;

        tbody.appendChild(tr);
        tbody.appendChild(inlineTr);
      });
      /* Manifiestos que no son microservicios: van en la MISMA tabla, con las
         mismas columnas (antes salían en un bloque aparte, que no era lo que
         se pedía: debían verse "como el resto de arriba"). */
      const extras = data.extra_manifests || [];
      if (extras.length) {
        const sep = document.createElement('tr');
        sep.className = 'deploy-extra-sep';
        sep.innerHTML = `<td colspan="8" style="padding:12px; font-size:12px; color:var(--text-muted); border-top:2px solid var(--card-border);">
            &#128230; <b style="color:var(--text);">Otros manifiestos del entorno</b>
            <span class="badge-pill" style="background:rgba(56,189,248,0.14); border:1px solid var(--card-border); font-size:10.5px; margin-left:6px;">${extras.length}</span>
            <span style="margin-left:6px;">&mdash; est&aacute;n en la carpeta de manifiestos pero no son microservicios del cat&aacute;logo.</span>
          </td>`;
        tbody.appendChild(sep);
        extras.forEach((m) => {
          const trExtra = document.createElement('tr');
          trExtra.className = 'deploy-extra-row';
          trExtra.innerHTML = celdasManifiestoExtra(m, envKey);
          /* Se enlazan aquí y no con onclick: la ruta va como dato, así una
             comilla en el nombre no rompe el atributo. */
          trExtra.querySelectorAll('[data-extra-deploy]').forEach((b) => {
            b.addEventListener('click', () => deployExtraManifest(envKey, b.dataset.extraDeploy));
          });
          trExtra.querySelectorAll('[data-extra-rollout]').forEach((b) => {
            b.addEventListener('click', () => rolloutRestartSingleDeploy(b.dataset.extraRollout));
          });
          trExtra.querySelectorAll('[data-extra-build]').forEach((b) => {
            b.addEventListener('click', () => openSingleBuildModal(b.dataset.extraBuild));
          });
          tbody.appendChild(trExtra);
        });
      }
      updateDeploySelectedCount();
      filterDeploymentTable();

      // Restaurar estado de tareas de construcción en curso o recientes
      for (const [svc, tid] of Object.entries(serviceBuildTaskMap)) {
        const task = activeBuildTasks[tid];
        if (task) {
          updateInlineBuildView(svc, task);
        }
      }
    }

    function filterDeploymentTable() {
      const q = (document.getElementById('deploySearchInput').value || '').toLowerCase();
      const rows = document.querySelectorAll('#deploymentsTableBody tr:not(.deploy-inline-row)');
      rows.forEach(r => {
        const text = r.innerText.toLowerCase();
        const matches = text.includes(q);
        r.style.display = matches ? '' : 'none';
        const svc = r.id.replace('deploy-row-', '');
        const inlineRow = document.getElementById(`deploy-inline-row-${svc}`);
        if (inlineRow) {
          if (!matches) {
            inlineRow.style.display = 'none';
          } else if (inlineRow.dataset.userOpen === 'true') {
            inlineRow.style.display = '';
          }
        }
      });
    }

    function clearDeployFilter() {
      const inp = document.getElementById('deploySearchInput');
      if (inp) {
        inp.value = '';
        filterDeploymentTable();
      }
    }

    /** Aplica un manifiesto del entorno con kubectl apply -f (requiere admin). */
    async function deployExtraManifest(envKey, archivo) {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => deployExtraManifest(envKey, archivo),
          `Desplegar '${archivo}' requiere rol Administrador / DevOps.`);
        return;
      }
      if (!confirm(`¿Aplicar '${archivo}' en el entorno ${envKey.toUpperCase()}?\n\nSe ejecutará kubectl apply -f sobre ese manifiesto.`)) return;
      showToast(`🚀 Aplicando ${archivo} en ${envKey.toUpperCase()}…`);
      try {
        const res = await fetch('/api/k8s/deploy_manifest', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ env: envKey, file: archivo })
        });
        const data = await res.json().catch(() => ({}));
        showToast(((res.ok && data.success !== false) ? '✅ ' : '⚠️ ') + (data.message || ('HTTP ' + res.status)));
      } catch (err) {
        showToast('⚠️ ' + err.message);
      }
      fetchDeploymentVersions();
    }

    /** Celdas (mismas columnas que los servicios) de un manifiesto que no es de
        un microservicio del catálogo. */
    function celdasManifiestoExtra(m, envKey) {
      const tieneVersion = !!m.yaml_version;
      let estado;
      if (!tieneVersion) {
        estado = '<span class="status-badge" style="opacity:.75;"><span class="dot"></span> Sin versión</span>';
      } else if (!m.k8s_version) {
        estado = '<span class="status-badge offline"><span class="dot"></span> No desplegado</span>';
      } else if (m.k8s_version === m.yaml_version) {
        estado = '<span class="status-badge online"><span class="dot"></span> Sincronizado</span>';
      } else {
        estado = '<span class="status-badge offline"><span class="dot"></span> Diferente</span>';
      }
      return `
        <td class="col-chk" style="text-align:center;" title="Manifiesto del entorno (no es un microservicio)">&#128230;</td>
        <td class="col-svc">
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <strong style="font-size:12px;">${escapeHtml(m.file)}</strong>
              ${m.kind ? `<span class="badge-pill" style="font-size:9.5px; background:rgba(148,163,184,0.14); border:1px solid var(--card-border); color:var(--text-muted);">${escapeHtml(m.kind)}</span>` : ''}
            </div>
            <small style="font-family:ui-monospace, monospace; color:var(--text-muted); font-size:10px;">${escapeHtml(m.deploy || m.file)}</small>
            ${m.construible
              ? `<small style="font-size:10px; color:var(--ok);">servicio del catálogo: <b>${escapeHtml(m.servicio_sugerido)}</b> (buildeable)</small>`
              : `<small style="font-size:10px; color:var(--text-muted);">${escapeHtml(m.motivo_build || 'no buildeable')} &mdash; s&iacute; se puede desplegar</small>`}
          </div>
        </td>
        <td class="col-branch"><span style="font-size:11px; color:var(--text-muted);">&mdash;</span></td>
        <td class="col-type" style="text-transform:uppercase; font-size:10px; color:var(--text-muted); font-weight:700;">${escapeHtml(m.categoria || 'Manifiesto')}</td>
        <td class="col-ver"><span style="font-family:ui-monospace, monospace; font-weight:700; font-size:12px; color:var(--accent);">${escapeHtml(m.yaml_version || '—')}</span></td>
        <td class="col-k8sver"><span style="font-family:ui-monospace, monospace; font-weight:700; font-size:12px;">${escapeHtml(m.k8s_version || '—')}</span></td>
        <td class="col-status">${estado}</td>
        <td class="col-actions">
          <div class="deploy-action-btns">
            ${m.construible ? `<button class="btn btn-sm" style="background:#0284c7; color:#fff; padding:3px 8px; font-size:11px;"
                    data-extra-build="${escapeHtml(m.servicio_sugerido)}"
                    title="Construir la imagen de ${escapeHtml(m.servicio_sugerido)} (tiene repo y Dockerfile)">&#128296; Build</button>` : ''}
            <button class="btn btn-sm" style="background:#0284c7; color:#fff; padding:3px 8px; font-size:11px;"
                    data-extra-deploy="${escapeHtml(m.file)}"
                    title="Aplicar este manifiesto en el entorno (kubectl apply -f)">&#128640; Desplegar</button>
            ${m.deploy ? `<button class="btn btn-sm btn-outline" style="padding:3px 8px; font-size:11px;"
                    data-extra-rollout="${escapeHtml(m.deploy)}"
                    title="Rollout restart de ${escapeHtml(m.deploy)}">&#128260; Rollout</button>` : ''}
            <a class="btn btn-sm btn-outline" style="padding:3px 8px; font-size:11px; text-decoration:none;"
               href="/api/site/yaml?env=${encodeURIComponent(envKey)}&file=${encodeURIComponent(m.file)}"
               target="_blank" rel="noopener" title="Ver el manifiesto completo">&#128196; Ver</a>
          </div>
        </td>`;
    }

    function onDeploySelectionChange(chk) {
      const name = chk.getAttribute('data-name');
      if (!name) return;
      if (chk.checked) deploySelection.add(name);
      else deploySelection.delete(name);
      updateDeploySelectedCount();
    }

    function toggleSelectAllDeploy(chk) {
      currentDeploymentList.forEach((s) => {
        if (chk.checked) deploySelection.add(s.name);
        else deploySelection.delete(s.name);
      });
      document.querySelectorAll('.deploy-chk').forEach((c) => { c.checked = chk.checked; });
      updateDeploySelectedCount();
    }

    /** Nombres seleccionados que aún existen en la tabla vigente. */
    function selectedDeployNames() {
      const vivos = new Set(currentDeploymentList.map((s) => s.name));
      Array.from(deploySelection).forEach((n) => { if (!vivos.has(n)) deploySelection.delete(n); });
      return Array.from(deploySelection);
    }

    function updateDeploySelectedCount() {
      const nombres = selectedDeployNames();
      /* Espejo en el DOM: si algo repintó las filas, se vuelve a marcar aquí. */
      document.querySelectorAll('.deploy-chk').forEach((c) => {
        c.checked = deploySelection.has(c.getAttribute('data-name'));
      });
      const lbl = document.getElementById('deploySelectedCount');
      if (lbl) lbl.innerText = `(${nombres.length} seleccionados)`;
      const n = nombres.length;
      const botones = [
        ['btnDeploySelected', `🚀 Desplegar seleccionados (${n})`],
        ['btnRolloutSelected', `🔄 Rollout seleccionados (${n})`],
      ];
      botones.forEach(([id, texto]) => {
        const b = document.getElementById(id);
        if (!b) return;
        b.textContent = texto;
        b.disabled = n === 0;
        b.style.opacity = n === 0 ? '0.55' : '';
        b.style.cursor = n === 0 ? 'not-allowed' : '';
      });
    }

    // Modal Editar Versión YAML
    function openEditYamlVersion(serviceName, currentVer) {
      editVersionTarget = { service: serviceName, env: document.getElementById('deployEnvSelect').value };
      document.getElementById('editYamlVersionTitle').innerText = `Editar Versión: ${serviceName}`;
      document.getElementById('editYamlVersionSubtitle').innerText = `Entorno seleccionado: ${editVersionTarget.env.toUpperCase()}`;
      document.getElementById('editYamlVersionInput').value = (currentVer !== '-' ? currentVer : '');
      document.getElementById('editYamlVersionModal').style.display = 'flex';
    }
    function closeEditYamlVersionModal() { document.getElementById('editYamlVersionModal').style.display = 'none'; }

    async function submitEditYamlVersion() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => submitEditYamlVersion(), "Modificar versiones YAML de manifiestos requiere rol Administrador / DevOps.");
        return;
      }
      const ver = document.getElementById('editYamlVersionInput').value.trim();
      if (!ver) { alert('Ingresa una versión válida.'); return; }
      closeEditYamlVersionModal();
      showToast(`Actualizando versión a ${ver} en ${editVersionTarget.service}...`);

      const res = await fetch('/api/deployments/update_version', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          service: editVersionTarget.service,
          version: ver,
          env: editVersionTarget.env
        })
      });
      const data = await res.json();
      showToast(data.message);
      fetchDeploymentVersions();
    }

    // Despliegues individuales y masivos
    async function deploySingleManifest(serviceName) {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => deploySingleManifest(serviceName), `Desplegar manifiesto de ${serviceName} requiere rol Administrador / DevOps.`);
        return;
      }
      const envKey = document.getElementById('deployEnvSelect').value;
      showToast(`Aplicando manifiesto K8s para ${serviceName} en ${envKey.toUpperCase()}...`);
      const res = await fetch('/api/k8s/deploy', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ service: serviceName, env: envKey })
      });
      const data = await res.json();
      showToast(data.message);

      let deployName = serviceName;
      if (currentDeploymentList && currentDeploymentList.length) {
        const s = currentDeploymentList.find(x => x.name === serviceName);
        if (s && s.k8s_deploy) deployName = s.k8s_deploy;
      }
      const ns = (envKey === 'main') ? 'prod' : envKey;
      trackRolloutStatus(deployName, ns);
      setTimeout(fetchDeploymentVersions, 2000);
    }

    function getSelectedMultiEnvs() {
      const chks = Array.from(document.querySelectorAll('.multi-env-chk:checked')).map(c => c.value);
      if (chks.length > 0) return chks;
      return [document.getElementById('deployEnvSelect').value || 'develop'];
    }

    function updateMultiEnvLabel() {
      const selected = Array.from(document.querySelectorAll('.multi-env-chk:checked')).map(c => c.value);
      let label = 'DEV';
      if (selected.length === 0) {
        label = (document.getElementById('deployEnvSelect').value || 'DEV').toUpperCase();
      } else if (selected.length === 3) {
        label = 'TODOS';
      } else {
        label = selected.map(e => (e === 'main' ? 'PROD' : e.toUpperCase())).join(' + ');
      }
      const b1 = document.getElementById('btnDeployEnvTag');
      if (b1) b1.innerText = label;
      const b2 = document.getElementById('btnRolloutEnvTag');
      if (b2) b2.innerText = label;
    }

    function toggleAllMultiEnv() {
      const chks = document.querySelectorAll('.multi-env-chk');
      const allChecked = Array.from(chks).every(c => c.checked);
      chks.forEach(c => c.checked = !allChecked);
      updateMultiEnvLabel();
    }

    function toggleMassiveDeployEnvs(checked) {
      const row = document.getElementById('massiveDeployEnvsRow');
      if (row) row.style.display = checked ? 'flex' : 'none';
    }

    function toggleAllMassEnv() {
      const chks = document.querySelectorAll('.mass-env-chk');
      const allChecked = Array.from(chks).every(c => c.checked);
      chks.forEach(c => c.checked = !allChecked);
    }

    async function deploySelectedManifests() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => deploySelectedManifests(), "Despliegues masivos K8s requieren rol Administrador / DevOps.");
        return;
      }
      const nombres = selectedDeployNames();
      if (nombres.length === 0) { alert('Selecciona al menos un servicio para desplegar.'); return; }

      const targetEnvs = getSelectedMultiEnvs();
      const envLabels = targetEnvs.map(e => (e === 'main' ? 'PROD' : e.toUpperCase())).join(', ');

      if (!confirm(`¿Desplegar los manifiestos K8s de los ${nombres.length} servicios seleccionados en [${envLabels}]?`)) return;

      for (const envKey of targetEnvs) {
        const ns = (envKey === 'main') ? 'prod' : envKey;
        showToast(`Iniciando despliegue hacia ${envKey.toUpperCase()} (ns: ${ns})...`);
        for (const name of nombres) {
          const deployName = (deployMetaByName.get(name) || {}).deploy || name;
          showToast(`[${envKey.toUpperCase()}] Desplegando ${name}...`);
          try {
            await fetch('/api/k8s/deploy', {
              method: 'POST',
              headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
              body: JSON.stringify({ service: name, env: envKey })
            });
            trackRolloutStatus(deployName, ns);
          } catch (e) {
            console.error(e);
          }
        }
      }
      showToast(`Despliegue completado en: ${envLabels}.`);
      fetchDeploymentVersions();
    }

    // Rollout de Deployments
    async function rolloutRestartSingleDeploy(deployName) {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => rolloutRestartSingleDeploy(deployName), `Rollout restart de '${deployName}' requiere rol Administrador / DevOps.`);
        return;
      }
      const envKey = document.getElementById('deployEnvSelect').value;
      const ns = (envKey === 'main') ? 'prod' : envKey;
      if (!confirm(`¿Ejecutar Rollout Restart en '${deployName}' (Namespace: ${ns})?`)) return;
      showToast(`Reiniciando deployment ${deployName}...`);
      const res = await fetch('/api/k8s/restart', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ deploy: deployName, namespace: ns })
      });
      const data = await res.json();
      showToast(data.message);
      trackRolloutStatus(deployName, ns);
      setTimeout(fetchDeploymentVersions, 2000);
    }

    async function rolloutSelectedDeployments() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => rolloutSelectedDeployments(), "Rollout masivo de deployments requiere rol Administrador / DevOps.");
        return;
      }
      const nombres = selectedDeployNames();
      if (nombres.length === 0) { alert('Selecciona al menos un microservicio.'); return; }

      const targetEnvs = getSelectedMultiEnvs();
      const deploys = nombres.map((n) => (deployMetaByName.get(n) || {}).deploy || n).filter(Boolean);
      const envLabels = targetEnvs.map(e => (e === 'main' ? 'PROD' : e.toUpperCase())).join(', ');

      if (!confirm(`¿Ejecutar Rollout Restart para los ${deploys.length} deployments seleccionados en [${envLabels}]?`)) return;

      for (const envKey of targetEnvs) {
        const ns = (envKey === 'main') ? 'prod' : envKey;
        showToast(`Reiniciando ${deploys.length} deployments en namespace '${ns}' (${envKey.toUpperCase()})...`);
        try {
          await fetch('/api/k8s/restart_multiple', {
            method: 'POST',
            headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ deployments: deploys, namespace: ns })
          });
          deploys.forEach(d => trackRolloutStatus(d, ns));
        } catch (e) {
          console.error(e);
        }
      }
      showToast(`Rollout completado en: ${envLabels}.`);
      setTimeout(fetchDeploymentVersions, 2000);
    }

    async function rolloutAllDeployments() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => rolloutAllDeployments(), "Rollout global en namespace requiere rol Administrador / DevOps.");
        return;
      }
      const envKey = document.getElementById('deployEnvSelect').value;
      const ns = (envKey === 'main') ? 'prod' : envKey;
      if (!confirm(`⚠️ ATENCIÓN: ¿Deseas reiniciar TODOS los deployments en el namespace '${ns}'?`)) return;

      showToast(`Reiniciando todos los deployments en '${ns}'...`);
      const res = await fetch('/api/k8s/rollout_all', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ namespace: ns })
      });
      const data = await res.json();
      showToast(data.message || "Rollout global enviado.");
      setTimeout(fetchDeploymentVersions, 2000);
    }

    // Modal Construcción Individual
    function openSingleBuildModal(serviceName) {
      const svc = (currentDeploymentList || []).find(s => s.name === serviceName);
      if (!svc) return;
      currentSingleBuildSvc = svc;

      document.getElementById('singleBuildTitle').innerText = `🛠️ Construir Imagen: ${svc.name}`;
      // El registry viene de la configuración de la instalación, no escrito en
      // el código: sin registry configurado la imagen es simplemente local.
      const buildRegistry = (globalData && globalData.registry) ? `${globalData.registry}/` : '';
      document.getElementById('singleBuildTargetImage').innerText = `${buildRegistry}${svc.image_name}:${svc.yaml_version !== '-' ? svc.yaml_version : 'latest'}`;
      const envKey = (document.getElementById('deployEnvSelect')?.value || 'develop');
      document.getElementById('singleBuildCurrentBranchLabel').innerText = `Rama actual del repositorio (${svc.local_branch || 'develop'})`;
      document.getElementById('singleBuildVersionInput').value = (svc.yaml_version !== '-' ? svc.yaml_version : '1.0.0');
      
      const envSelect = document.getElementById('singleBuildEnvSelect');
      if (envSelect) envSelect.value = envKey;
      handleSingleBuildEnvChange(envKey);

      const targetRadio = document.querySelector(`input[name="singleBuildBranchRadio"][value="${envKey}"]`);
      if (targetRadio) {
        targetRadio.checked = true;
      } else {
        document.querySelector('input[name="singleBuildBranchRadio"][value="current"]').checked = true;
      }
      toggleSingleCustomBranch(false);
      document.getElementById('singleCustomBranchInput').value = '';
      document.getElementById('singleBuildOptPush').checked = true;
      document.getElementById('singleBuildOptYaml').checked = true;
      document.getElementById('singleBuildOptDeploy').checked = false;
      document.getElementById('singleBuildOptRollout').checked = false;

      const authorVal = localStorage.getItem('sisper_gitlab_author') || 'dgomezh';
      const aInp = document.getElementById('singleBuildAuthorInput');
      if (aInp) aInp.value = authorVal;

      document.getElementById('singleBuildModal').style.display = 'flex';
    }

    function handleSingleBuildEnvChange(envKey) {
      const targetRadio = document.querySelector(`input[name="singleBuildBranchRadio"][value="${envKey}"]`);
      if (targetRadio) targetRadio.checked = true;
      const yamlFolderMap = { 'develop': '01_deploy_develop', 'test': '02_deploy_test', 'main': '03_deploy_prod' };
      const ns = (envKey === 'main') ? 'prod' : envKey;
      const yamlFolder = yamlFolderMap[envKey] || envKey;
      
      const lblYaml = document.getElementById('singleBuildOptYamlLabel');
      if (lblYaml) lblYaml.innerHTML = `<strong>3. Actualizar manifiesto YAML</strong> (<code>${yamlFolder}</code>)`;
      
      const lblDeploy = document.getElementById('singleBuildOptDeployLabel');
      if (lblDeploy) lblDeploy.innerHTML = `<strong>4. Desplegar en Kubernetes</strong> (<code>kubectl apply</code> en namespace '<strong>${ns}</strong>')`;
      
      const lblRollout = document.getElementById('singleBuildOptRolloutLabel');
      if (lblRollout) lblRollout.innerHTML = `<strong>5. Reiniciar pods en K8s</strong> (<code>kubectl rollout restart</code> en '<strong>${ns}</strong>')`;
    }

    function closeSingleBuildModal() {
      document.getElementById('singleBuildModal').style.display = 'none';
    }

    function toggleSingleCustomBranch(show) {
      document.getElementById('singleCustomBranchContainer').style.display = show ? 'block' : 'none';
    }

    function bumpSingleBuildVersion(type) {
      const input = document.getElementById('singleBuildVersionInput');
      let ver = input.value.trim().replace(/^v/, '');
      const parts = ver.split('.').map(n => parseInt(n, 10));
      if (parts.length >= 3 && !parts.some(isNaN)) {
        if (type === 'patch') parts[2] += 1;
        else if (type === 'minor') { parts[1] += 1; parts[2] = 0; }
        input.value = parts.join('.');
      } else {
        input.value = ver + '.1';
      }
    }

    async function submitSingleBuild() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => submitSingleBuild(), "Construcción de imágenes requiere rol Administrador / DevOps.");
        return;
      }
      if (!currentSingleBuildSvc) return;
      const branchOption = document.querySelector('input[name="singleBuildBranchRadio"]:checked').value;
      const customBranch = document.getElementById('singleCustomBranchInput').value.trim();
      const versionTag = document.getElementById('singleBuildVersionInput').value.trim();
      const authorName = (document.getElementById('singleBuildAuthorInput')?.value || '').trim();
      const doPush = document.getElementById('singleBuildOptPush').checked;
      const doNoCache = document.getElementById('singleBuildOptNoCache').checked;
      const doYaml = document.getElementById('singleBuildOptYaml').checked;
      const doDeploy = document.getElementById('singleBuildOptDeploy').checked;
      const doRollout = document.getElementById('singleBuildOptRollout').checked;
      const targetEnv = (document.getElementById('singleBuildEnvSelect')?.value || document.getElementById('deployEnvSelect').value);

      if (branchOption === 'custom' && !customBranch) {
        alert('Ingresa el nombre de la rama personalizada.');
        return;
      }
      if (!versionTag) {
        alert('Ingresa un tag de versión válido.');
        return;
      }

      if (authorName) localStorage.setItem('sisper_gitlab_author', authorName);
      closeSingleBuildModal();

      const payload = {
        services: [currentSingleBuildSvc.name],
        branch: branchOption,
        custom_branch: customBranch,
        version_tag: versionTag,
        author: authorName,
        push: doPush,
        no_cache: doNoCache,
        update_yaml: doYaml,
        deploy: doDeploy,
        rollout: doRollout,
        target_env: targetEnv
      };

      const res = await fetch('/api/deployments/build', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success && data.task_id) {
        const svcName = currentSingleBuildSvc.name;
        serviceBuildTaskMap[svcName] = data.task_id;
        openInlineBuildTerminal(svcName, data.task_id, `Construcción: ${svcName}:${versionTag}`);
        showToast(`Construcción iniciada para ${svcName}. Mostrando consola inline.`);
      } else {
        alert('Error al iniciar tarea de construcción.');
      }
    }

    // Modal Construcción Masiva
    function openMassiveBuildModal() {
      const container = document.getElementById('massiveServicesContainer');
      container.innerHTML = '';

      (currentDeploymentList || []).forEach(s => {
        const isSelected = document.querySelector(`.deploy-chk[data-name="${s.name}"]:checked`) !== null;
        const label = document.createElement('label');
        label.style = "display:flex; align-items:center; gap:6px; font-size:11px; cursor:pointer;";
        label.innerHTML = `
          <input type="checkbox" class="mass-build-svc-chk" value="${s.name}" data-type="${s.type}" ${isSelected ? 'checked' : ''}>
          <span><strong>${s.name}</strong> <small style="color:var(--text-muted); font-size:10px;">(${s.current_branch})</small></span>
        `;
        container.appendChild(label);
      });

      const authorVal = localStorage.getItem('sisper_gitlab_author') || 'dgomezh';
      const aInp = document.getElementById('massiveBuildAuthorInput');
      if (aInp) aInp.value = authorVal;

      // Sincronizar checkboxes de entornos con los seleccionados en la barra multi-env
      const activeEnvs = getSelectedMultiEnvs();
      document.querySelectorAll('.mass-env-chk').forEach(c => {
        c.checked = activeEnvs.includes(c.value);
      });
      const deployOpt = document.getElementById('massiveOptDeploy');
      toggleMassiveDeployEnvs(deployOpt ? deployOpt.checked : false);

      document.getElementById('massiveBuildModal').style.display = 'flex';
    }

    function closeMassiveBuildModal() {
      document.getElementById('massiveBuildModal').style.display = 'none';
    }

    function setMassivePresets(type) {
      document.querySelectorAll('.mass-build-svc-chk').forEach(c => {
        if (type === 'all') c.checked = true;
        else if (type === 'none') c.checked = false;
        else if (type === 'backend') c.checked = (c.getAttribute('data-type') === 'backend');
        else if (type === 'frontend') c.checked = (c.getAttribute('data-type') === 'frontend');
      });
    }

    async function submitMassiveBuild() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => submitMassiveBuild(), "Construcción masiva de imágenes requiere rol Administrador / DevOps.");
        return;
      }
      const selectedSvcs = Array.from(document.querySelectorAll('.mass-build-svc-chk:checked')).map(c => c.value);
      if (selectedSvcs.length === 0) {
        alert('Selecciona al menos un microservicio para construir.');
        return;
      }

      const branchStrategy = document.getElementById('massiveBranchSelect').value;
      const authorName = (document.getElementById('massiveBuildAuthorInput')?.value || '').trim();
      const doPush = document.getElementById('massiveOptPush').checked;
      const doNoCache = document.getElementById('massiveOptNoCache').checked;
      const doDeploy = document.getElementById('massiveOptDeploy').checked;
      const doRollout = document.getElementById('massiveOptRollout').checked;
      const massEnvs = Array.from(document.querySelectorAll('.mass-env-chk:checked')).map(c => c.value);
      const targetEnvs = (massEnvs.length > 0) ? massEnvs : [document.getElementById('deployEnvSelect').value || 'develop'];
      const targetEnv = targetEnvs[0];

      if (authorName) localStorage.setItem('sisper_gitlab_author', authorName);
      closeMassiveBuildModal();

      const payload = {
        services: selectedSvcs,
        branch: branchStrategy,
        version_tag: "",
        author: authorName,
        push: doPush,
        no_cache: doNoCache,
        update_yaml: doDeploy,
        deploy: doDeploy,
        rollout: doRollout,
        target_env: targetEnv,
        target_envs: targetEnvs
      };

      /* Una tarea por servicio con tope de concurrencia.  Antes se mandaba TODO
         en una sola tarea y el backend (`run_build_task`) los construía en serie,
         uno detrás de otro: con 12 servicios eso es esperar 12 builds.  Cada
         servicio recibe su propia tarea y su propia consola, y se mantienen
         `MAX_BUILD_PARALELO` construyendo a la vez para no saturar la máquina. */
      const cola = selectedSvcs.slice();
      let enCurso = 0;
      let lanzadas = 0;
      let fallidas = 0;

      const bombear = () => {
        while (enCurso < MAX_BUILD_PARALELO && cola.length) {
          const svc = cola.shift();
          enCurso++;
          lanzadas++;
          delete activeBuildTasks[serviceBuildTaskMap[svc] || ''];
          updateSvcBuildBadge(svc, 'queued', '⏳ En cola');
          fetch('/api/deployments/build', {
            method: 'POST',
            headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ ...payload, services: [svc] })
          }).then((r) => r.json()).then((data) => {
            if (data.success && data.task_id) {
              serviceBuildTaskMap[svc] = data.task_id;
              openInlineBuildTerminal(svc, data.task_id, `Construcción: ${svc}`);
            } else {
              fallidas++;
              updateSvcBuildBadge(svc, 'failed', '❌ No iniciada');
            }
          }).catch(() => {
            fallidas++;
            updateSvcBuildBadge(svc, 'failed', '❌ No iniciada');
          }).finally(() => {
            enCurso--;
            if (cola.length) bombear();
            else if (enCurso === 0) {
              showToast(fallidas
                ? `⚠️ ${lanzadas - fallidas}/${lanzadas} construcciones en marcha (${fallidas} no arrancaron).`
                : `✅ ${lanzadas} construcciones en marcha (hasta ${MAX_BUILD_PARALELO} a la vez).`);
            }
          });
        }
      };
      showToast(`🛠️ Lanzando ${selectedSvcs.length} construcciones (hasta ${MAX_BUILD_PARALELO} en paralelo)...`);
      bombear();
    }

    async function inspectImageModal(imageName, tag) {
      const modal = document.getElementById('imageInspectModal');
      const content = document.getElementById('imageInspectContent');
      content.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Cargando metadatos para <code>${imageName}:${tag}</code>...</div>`;
      modal.style.display = 'flex';

      try {
        const res = await fetch(`/api/deployments/inspect?image=${encodeURIComponent(imageName)}&tag=${encodeURIComponent(tag)}`);
        const data = await res.json();
        
        let labelRows = '';
        if (data.labels && Object.keys(data.labels).length > 0) {
          for (const [k, v] of Object.entries(data.labels)) {
            labelRows += `<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
              <td style="font-family:ui-monospace, monospace; color:var(--accent); font-weight:700; width:45%; padding:4px 6px;">${k}</td>
              <td style="font-family:ui-monospace, monospace; color:#cbd5e1; word-break:break-all; padding:4px 6px;">${v}</td>
            </tr>`;
          }
        } else {
          labelRows = `<tr><td colspan="2" style="color:var(--text-muted); padding:8px;">Sin etiquetas adicionales detectadas.</td></tr>`;
        }

        content.innerHTML = `
          <div style="background:#111827; padding:10px 14px; border-radius:8px; border:1px solid #1f2937;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:11px; color:var(--text-muted);">REFERENCIA DE IMAGEN:</span>
              <span class="badge-pill badge-clean" style="font-size:10px;">${data.source === 'podman-local' ? 'PODMAN LOCAL' : (data.source === 'registry-skopeo' ? 'REGISTRY GITLAB' : 'NO DISPONIBLE')}</span>
            </div>
            <div style="font-family:ui-monospace, monospace; font-weight:700; color:var(--accent); font-size:13px; margin-top:2px;">
              ${data.image}
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div style="background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <div style="font-size:10px; color:var(--text-muted); font-weight:700;">👤 CONSTRUIDA POR (BUILDER):</div>
              <div style="font-weight:700; color:#38bdf8; font-size:12px; margin-top:2px;">${data.builder || data.author}</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <div style="font-size:10px; color:var(--text-muted); font-weight:700;">🌿 AUTOR ÚLTIMO COMMIT (GIT):</div>
              <div style="font-weight:700; color:#a78bfa; font-size:12px; margin-top:2px;">${data.commit_author || 'No Disponible'}</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <div style="font-size:10px; color:var(--text-muted); font-weight:700;">📅 FECHA DE CREACIÓN:</div>
              <div style="font-weight:700; color:#cbd5e1; font-size:12px; margin-top:2px;">${data.created}</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <div style="font-size:10px; color:var(--text-muted); font-weight:700;">💻 HOST / RUNNER:</div>
              <div style="font-family:ui-monospace, monospace; font-size:11px; color:#cbd5e1; margin-top:2px;">${data.host} (${data.runner})</div>
            </div>
          </div>

          <div>
            <div style="font-weight:700; font-size:11px; color:var(--text-muted); margin-bottom:4px; text-transform:uppercase;">
              Etiquetas Registradas (Labels OCI):
            </div>
            <div style="max-height:160px; overflow-y:auto; border:1px solid rgba(255,255,255,0.08); border-radius:6px; background:#000;">
              <table style="width:100%; font-size:11px;">
                <tbody>${labelRows}</tbody>
              </table>
            </div>
          </div>
        `;
      } catch (err) {
        content.innerHTML = `<div style="color:var(--danger); padding:10px;">Error al consultar metadatos de la imagen: ${err}</div>`;
      }
    }

    function closeImageInspectModal() {
      document.getElementById('imageInspectModal').style.display = 'none';
    }

    // -------------------------------------------------------------------------
    // Consola de Build Inline por Microservicio & Popout Modal
    // -------------------------------------------------------------------------
    function openInlineBuildTerminal(svcName, taskId, title) {
      currentBuildTaskId = taskId;
      if (!activeBuildTasks[taskId]) {
        activeBuildTasks[taskId] = {
          taskId: taskId,
          title: title || `⚙️ Construcción: ${svcName}`,
          progress: 5,
          current_step: "Iniciando conexión con runner...",
          status: "running",
          logs: ["Conectando al log de construcción..."],
          svc_logs: {},
          services: [svcName],
          current_service: svcName,
          minimized: false
        };
      } else {
        if (title) activeBuildTasks[taskId].title = title;
      }

      serviceBuildTaskMap[svcName] = taskId;
      expandInlineBuildRow(svcName);
      updateInlineBuildView(svcName, activeBuildTasks[taskId]);

      if (!buildPollInterval) {
        buildPollInterval = setInterval(pollAllBuildTasks, 1200);
      }
      pollAllBuildTasks();
    }

    function expandInlineBuildRow(svcName) {
      const row = document.getElementById(`deploy-inline-row-${svcName}`);
      if (row) {
        row.style.display = '';
        row.dataset.userOpen = 'true';
        const logBtn = document.getElementById(`btn-inline-log-${svcName}`);
        if (logBtn) logBtn.style.display = 'inline-flex';
        const mainRow = document.getElementById(`deploy-row-${svcName}`);
        if (mainRow) {
          mainRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    }

    function collapseInlineBuildRow(svcName) {
      const row = document.getElementById(`deploy-inline-row-${svcName}`);
      if (row) {
        row.style.display = 'none';
        row.dataset.userOpen = 'false';
        showToast(`Consola minimizada a la fila de ${svcName}.`);
      }
    }

    function toggleInlineBuildRow(svcName) {
      const row = document.getElementById(`deploy-inline-row-${svcName}`);
      if (!row) return;
      if (row.style.display === 'none') {
        expandInlineBuildRow(svcName);
      } else {
        collapseInlineBuildRow(svcName);
      }
    }

    function closeInlineBuildRow(svcName) {
      const row = document.getElementById(`deploy-inline-row-${svcName}`);
      if (row) {
        row.style.display = 'none';
        row.dataset.userOpen = 'false';
      }
    }

    function copyInlineBuildLogs(svcName) {
      const b = document.getElementById(`inline-terminal-${svcName}`);
      if (b) {
        navigator.clipboard.writeText(b.innerText);
        showToast(`Logs de ${svcName} copiados al portapapeles.`);
      }
    }

    function toggleInlineAutoScroll(svcName) {
      const b = document.getElementById(`inline-terminal-${svcName}`);
      const btn = document.getElementById(`btn-autoscroll-${svcName}`);
      if (!b || !btn) return;
      const cur = b.getAttribute('data-autoscroll') !== 'false';
      if (cur) {
        b.setAttribute('data-autoscroll', 'false');
        btn.innerText = '⏸️ Auto-scroll: OFF';
        btn.style.color = '#94a3b8';
      } else {
        b.setAttribute('data-autoscroll', 'true');
        btn.innerText = '⬇️ Auto-scroll: ON';
        btn.style.color = '#38bdf8';
        b.scrollTop = b.scrollHeight;
      }
    }

    function toggleInlineHeight(svcName) {
      const b = document.getElementById(`inline-terminal-${svcName}`);
      if (b) {
        b.classList.toggle('expanded');
      }
    }

    function popoutToModal(svcName) {
      const taskId = serviceBuildTaskMap[svcName] || currentBuildTaskId;
      if (taskId && activeBuildTasks[taskId]) {
        openBuildTerminal(taskId, activeBuildTasks[taskId].title);
      }
    }

    function updateSvcBuildBadge(svcName, status, label) {
      const badgeEl = document.getElementById(`svc-build-badge-${svcName}`);
      if (!badgeEl) return;
      if (status === 'running') {
        badgeEl.innerHTML = `<span class="svc-build-pill running"><span class="dot"></span> ${label || 'Construyendo'}</span>`;
      } else if (status === 'completed') {
        badgeEl.innerHTML = `<span class="svc-build-pill completed">✅ ${label || 'OK'}</span>`;
      } else if (status === 'failed') {
        badgeEl.innerHTML = `<span class="svc-build-pill failed">❌ ${label || 'Error'}</span>`;
      } else if (status === 'queued') {
        badgeEl.innerHTML = `<span class="svc-build-pill queued">${label || '⏳ En cola'}</span>`;
      } else {
        badgeEl.innerHTML = '';
      }
    }

    function updateInlineBuildView(svcName, task) {
      if (!task) return;
      const isRunning = task.status === 'running';
      const isCompleted = task.status === 'completed';
      const isFailed = task.status === 'failed';

      let specificStatus = 'running';
      if (task.service_status && task.service_status[svcName]) {
        specificStatus = task.service_status[svcName];
      } else if (isCompleted) {
        specificStatus = 'completed';
      } else if (isFailed) {
        specificStatus = 'failed';
      }

      // 1. Badge en la celda del Microservicio
      const badgeEl = document.getElementById(`svc-build-badge-${svcName}`);
      if (badgeEl) {
        if (specificStatus === 'building' || (isRunning && task.current_service === svcName)) {
          badgeEl.innerHTML = `<span class="svc-build-pill running"><span class="dot"></span> ⚙️ ${task.progress}%</span>`;
        } else if (specificStatus === 'queued') {
          badgeEl.innerHTML = `<span class="svc-build-pill queued">⏳ En cola</span>`;
        } else if (specificStatus === 'completed') {
          badgeEl.innerHTML = `<span class="svc-build-pill completed">✅ OK</span>`;
        } else if (specificStatus === 'failed') {
          badgeEl.innerHTML = `<span class="svc-build-pill failed">❌ Error</span>`;
        } else {
          badgeEl.innerHTML = '';
        }
      }

      // 2. Botón de Log en la celda de Acciones
      const btnLog = document.getElementById(`btn-inline-log-${svcName}`);
      if (btnLog) {
        btnLog.style.display = 'inline-flex';
        if (specificStatus === 'building' || (isRunning && task.current_service === svcName)) {
          btnLog.innerHTML = `📺 Log (${task.progress}%)`;
          btnLog.style.color = '#38bdf8';
          btnLog.style.borderColor = '#0284c7';
        } else if (specificStatus === 'completed') {
          btnLog.innerHTML = `📺 Log ✅`;
          btnLog.style.color = '#34d399';
          btnLog.style.borderColor = '#10b981';
        } else if (specificStatus === 'failed') {
          btnLog.innerHTML = `📺 Log ❌`;
          btnLog.style.color = '#f87171';
          btnLog.style.borderColor = '#ef4444';
        } else {
          btnLog.innerHTML = `📺 Log`;
        }
      }

      // 3. Consola Inline
      const titleEl = document.getElementById(`inline-title-${svcName}`);
      if (titleEl) titleEl.innerText = `Consola: ${svcName}`;

      const iconEl = document.getElementById(`inline-status-icon-${svcName}`);
      if (iconEl) {
        iconEl.innerText = (specificStatus === 'completed' ? '✅' : (specificStatus === 'failed' ? '❌' : '⚙️'));
      }

      const inlineBadge = document.getElementById(`inline-badge-${svcName}`);
      if (inlineBadge) {
        if (specificStatus === 'completed') {
          inlineBadge.className = 'status-badge online';
          inlineBadge.innerHTML = '<span class="dot"></span> COMPLETADO ✅';
        } else if (specificStatus === 'failed') {
          inlineBadge.className = 'status-badge offline';
          inlineBadge.innerHTML = '<span class="dot"></span> ERROR ❌';
        } else if (specificStatus === 'queued') {
          inlineBadge.className = 'status-badge offline';
          inlineBadge.style.color = '#fbbf24';
          inlineBadge.innerHTML = '<span class="dot" style="background:#f59e0b;"></span> EN COLA';
        } else {
          inlineBadge.className = 'status-badge online';
          inlineBadge.innerHTML = '<span class="dot"></span> EN EJECUCIÓN';
        }
      }

      const stepEl = document.getElementById(`inline-step-${svcName}`);
      if (stepEl) {
        stepEl.innerText = task.current_step || 'Construyendo imagen...';
      }

      const progEl = document.getElementById(`inline-progress-${svcName}`);
      if (progEl) {
        progEl.style.width = `${task.progress || 0}%`;
        if (specificStatus === 'completed') {
          progEl.style.background = '#10b981';
        } else if (specificStatus === 'failed') {
          progEl.style.background = '#ef4444';
        } else {
          progEl.style.background = 'var(--accent)';
        }
      }

      // Logs: si existen logs específicos del servicio los mostramos, sino los logs de la tarea
      let logsToDisplay = [];
      if (task.svc_logs && task.svc_logs[svcName] && task.svc_logs[svcName].length > 0) {
        logsToDisplay = task.svc_logs[svcName];
      } else if (task.logs && task.logs.length > 0) {
        logsToDisplay = task.logs;
      }

      const termBody = document.getElementById(`inline-terminal-${svcName}`);
      if (termBody) {
        termBody.innerText = logsToDisplay.length > 0 ? logsToDisplay.join(String.fromCharCode(10)) : 'Esperando logs del runner...';
        if (termBody.getAttribute('data-autoscroll') !== 'false') {
          termBody.scrollTop = termBody.scrollHeight;
        }
      }

      const linesEl = document.getElementById(`inline-lines-${svcName}`);
      if (linesEl) {
        linesEl.innerText = `${logsToDisplay.length} líneas`;
      }
    }

    function openBuildTerminal(taskId, title) {
      currentBuildTaskId = taskId;
      if (!activeBuildTasks[taskId]) {
        activeBuildTasks[taskId] = {
          taskId: taskId,
          title: title || "⚙️ Construcción CI/CD",
          progress: 5,
          current_step: "Iniciando conexión con runner...",
          status: "running",
          logs: ["Conectando al log de construcción..."],
          minimized: false
        };
      } else {
        activeBuildTasks[taskId].minimized = false;
        if (title) activeBuildTasks[taskId].title = title;
      }

      const task = activeBuildTasks[taskId];
      document.getElementById('buildTerminalTitle').innerText = task.title;
      document.getElementById('buildTerminalBadge').className = "status-badge online";
      document.getElementById('buildTerminalBadge').innerHTML = '<span class="dot"></span> EN EJECUCIÓN';
      document.getElementById('buildTerminalProgressBar').style.width = `${task.progress}%`;
      document.getElementById('buildTerminalPercent').innerText = `${task.progress}%`;
      document.getElementById('buildTerminalStepText').innerText = task.current_step;
      document.getElementById('buildTerminalBody').innerText = task.logs.join(String.fromCharCode(10));
      document.getElementById('buildTerminalLinesCount').innerText = `${task.logs.length} líneas`;
      document.getElementById('buildTerminalModal').style.display = 'flex';

      renderBuildTaskTabs();
      renderBuildTasksDock();

      if (!buildPollInterval) {
        buildPollInterval = setInterval(pollAllBuildTasks, 1200);
      }
      pollAllBuildTasks();
    }

    function switchBuildModalTask(taskId) {
      if (!activeBuildTasks[taskId]) return;
      currentBuildTaskId = taskId;
      const task = activeBuildTasks[taskId];
      document.getElementById('buildTerminalTitle').innerText = task.title;

      const pct = `${task.progress || 0}%`;
      document.getElementById('buildTerminalProgressBar').style.width = pct;
      document.getElementById('buildTerminalPercent').innerText = pct;
      document.getElementById('buildTerminalStepText').innerText = task.current_step || '';

      const badge = document.getElementById('buildTerminalBadge');
      if (task.status === 'completed') {
        badge.className = "status-badge online";
        badge.innerHTML = '<span class="dot"></span> COMPLETADO ✅';
      } else if (task.status === 'failed') {
        badge.className = "status-badge offline";
        badge.innerHTML = '<span class="dot"></span> ERROR ❌';
      } else {
        badge.className = "status-badge online";
        badge.innerHTML = '<span class="dot"></span> EN EJECUCIÓN';
      }

      const body = document.getElementById('buildTerminalBody');
      body.innerText = (task.logs || []).join(String.fromCharCode(10));
      document.getElementById('buildTerminalLinesCount').innerText = `${(task.logs || []).length} líneas`;
      scrollBuildLogsToBottom();
      renderBuildTaskTabs();
    }

    function renderBuildTaskTabs() {
      const container = document.getElementById('buildModalTaskTabs');
      if (!container) return;
      const taskIds = Object.keys(activeBuildTasks);
      if (taskIds.length <= 1) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
      }
      container.style.display = 'flex';
      container.innerHTML = taskIds.map(tid => {
        const t = activeBuildTasks[tid];
        const isCurrent = tid === currentBuildTaskId;
        const isRunning = t.status === 'running';
        const isCompleted = t.status === 'completed';
        const statusIcon = isRunning ? '⚙️' : (isCompleted ? '✅' : '❌');
        const bg = isCurrent ? '#0284c7' : '#1e293b';
        const fg = isCurrent ? '#ffffff' : '#94a3b8';
        const border = isCurrent ? '1px solid #38bdf8' : '1px solid #334155';
        return `
          <div style="background:${bg}; border:${border}; border-radius:6px; padding:3px 8px; font-size:11px; font-weight:600; color:${fg}; cursor:pointer; display:inline-flex; align-items:center; gap:6px; white-space:nowrap;" onclick="switchBuildModalTask('${tid}')">
            <span>${statusIcon} ${t.title} (${t.progress}%)</span>
            <button onclick="event.stopPropagation(); dismissBuildTask('${tid}')" style="background:none; border:none; color:${fg}; opacity:0.7; font-size:13px; cursor:pointer; padding:0; line-height:1;" title="Cerrar pestaña">&times;</button>
          </div>
        `;
      }).join('');
    }

    function renderBuildTasksDock() {
      const dock = document.getElementById('buildTasksDock');
      if (dock) {
        dock.style.display = 'none';
        dock.innerHTML = '';
      }
    }

    function minimizeBuildTerminal() {
      if (currentBuildTaskId && activeBuildTasks[currentBuildTaskId]) {
        activeBuildTasks[currentBuildTaskId].minimized = true;
        const svc = activeBuildTasks[currentBuildTaskId].current_service || (activeBuildTasks[currentBuildTaskId].services || [])[0];
        if (svc) {
          expandInlineBuildRow(svc);
        }
      }
      document.getElementById('buildTerminalModal').style.display = 'none';
      renderBuildTasksDock();
      showToast("Proceso minimizado a la tabla de despliegues.");
    }

    function restoreBuildTerminal(taskId) {
      const targetId = taskId || currentBuildTaskId || Object.keys(activeBuildTasks)[0];
      if (!targetId) return;
      if (activeBuildTasks[targetId]) {
        activeBuildTasks[targetId].minimized = false;
      }
      openBuildTerminal(targetId, activeBuildTasks[targetId]?.title);
    }

    function dismissBuildTask(taskId) {
      if (activeBuildTasks[taskId]) {
        delete activeBuildTasks[taskId];
      }
      if (currentBuildTaskId === taskId) {
        const remaining = Object.keys(activeBuildTasks);
        if (remaining.length > 0) {
          switchBuildModalTask(remaining[0]);
        } else {
          closeBuildTerminalModal();
        }
      }
      renderBuildTaskTabs();
      renderBuildTasksDock();
    }

    async function pollAllBuildTasks() {
      const taskIds = Object.keys(activeBuildTasks);
      if (taskIds.length === 0) {
        if (buildPollInterval) {
          clearInterval(buildPollInterval);
          buildPollInterval = null;
        }
        return;
      }

      let anyRunning = false;
      for (const tid of taskIds) {
        const task = activeBuildTasks[tid];
        if (task.status === 'running') {
          anyRunning = true;
          try {
            const res = await fetch(`/api/deployments/build_status?task_id=${tid}`);
            if (res.ok) {
              const data = await res.json();
              task.progress = data.progress || 0;
              task.current_step = data.current_step || '';
              task.logs = data.logs || [];
              task.status = data.status || 'running';
              task.services = data.services || task.services || [];
              task.current_service = data.current_service || '';
              task.service_status = data.service_status || {};
              task.svc_logs = data.svc_logs || {};

              // Actualizar consola y badge inline para cada microservicio participante
              const svcs = (task.services && task.services.length > 0) ? task.services : (task.current_service ? [task.current_service] : []);
              svcs.forEach(sName => {
                serviceBuildTaskMap[sName] = tid;
                updateInlineBuildView(sName, task);
              });

              if (data.status === 'completed' || data.status === 'failed') {
                if (data.status === 'completed') {
                  showToast(`Construcción finalizada: ${task.title} ✅`);
                } else {
                  showToast(`Error en construcción: ${task.title} ❌`);
                  const buildModal = document.getElementById('buildTerminalModal');
                  if (!buildModal || buildModal.style.display === 'none') {
                    const rawLogs = (task.logs && task.logs.length > 0)
                      ? task.logs.slice(-40).join('\n')
                      : (data.error || 'La tarea de construcción terminó con código de error.');
                    openCommandModal({
                      title: `Fallo en Construcción — ${task.title}`,
                      subtitle: `Microservicio(s): ${svcs.join(', ') || 'N/A'} | Paso: ${task.current_step || 'Build'}`,
                      command: 'podman build / skopeo / kubectl',
                      status: 'error',
                      output: rawLogs
                    });
                  }
                }
                fetchDeploymentVersions();
              }
            }
          } catch (err) {
            console.error("Error consultando build task:", tid, err);
          }
        }
      }

      const modal = document.getElementById('buildTerminalModal');
      if (modal && modal.style.display !== 'none' && currentBuildTaskId && activeBuildTasks[currentBuildTaskId]) {
        const cur = activeBuildTasks[currentBuildTaskId];
        const pct = `${cur.progress || 0}%`;
        document.getElementById('buildTerminalProgressBar').style.width = pct;
        document.getElementById('buildTerminalPercent').innerText = pct;
        document.getElementById('buildTerminalStepText').innerText = cur.current_step || '';

        const badge = document.getElementById('buildTerminalBadge');
        if (cur.status === 'completed') {
          badge.className = "status-badge online";
          badge.innerHTML = '<span class="dot"></span> COMPLETADO ✅';
        } else if (cur.status === 'failed') {
          badge.className = "status-badge offline";
          badge.innerHTML = '<span class="dot"></span> ERROR ❌';
        } else {
          badge.className = "status-badge online";
          badge.innerHTML = '<span class="dot"></span> EN EJECUCIÓN';
        }

        const body = document.getElementById('buildTerminalBody');
        body.innerText = (cur.logs || []).join(String.fromCharCode(10));
        document.getElementById('buildTerminalLinesCount').innerText = `${(cur.logs || []).length} líneas`;
        body.scrollTop = body.scrollHeight;
      }

      renderBuildTaskTabs();
      renderBuildTasksDock();

      if (!anyRunning) {
        if (buildPollInterval) {
          clearInterval(buildPollInterval);
          buildPollInterval = null;
        }
      }
    }

    function closeBuildTerminalModal() {
      document.getElementById('buildTerminalModal').style.display = 'none';
      if (currentBuildTaskId && activeBuildTasks[currentBuildTaskId]) {
        activeBuildTasks[currentBuildTaskId].minimized = true;
      }
      renderBuildTasksDock();
    }

    function copyBuildLogs() {
      const text = document.getElementById('buildTerminalBody').innerText;
      navigator.clipboard.writeText(text);
      showToast("Logs de construcción copiados.");
    }

    function scrollBuildLogsToBottom() {
      const b = document.getElementById('buildTerminalBody');
      b.scrollTop = b.scrollHeight;
    }

    // -------------------------------------------------------------------------
    // Git Manifiestos K8s (backend/config)
    // -------------------------------------------------------------------------
    async function refreshConfigGitStatus() {
      const badge = document.getElementById('configGitBranchStatus');
      if (!badge) return;
      try {
        const res = await fetch('/api/config_git/status');
        if (!res.ok) return;
        const data = await res.json();
        let html = `🌿 Rama: <strong>${data.branch}</strong> | Modificados: <span style="color:${data.dirty > 0 ? '#f59e0b' : '#34d399'}; font-weight:700;">${data.dirty}</span>`;
        if (data.ahead > 0) html += ` | <span style="color:#38bdf8;">⬆️ +${data.ahead}</span>`;
        if (data.behind > 0) html += ` | <span style="color:#f87171;">⬇️ -${data.behind}</span>`;
        badge.innerHTML = html;
      } catch (e) {
        badge.innerHTML = '<span style="color:var(--text-muted);">Sin datos Git</span>';
      }
    }

    async function configGitPull() {
      if (!ensureDevOrAdminAuth()) return;
      openCommandModal({
        title: 'Git Pull — backend/config',
        subtitle: 'Sincronización de Manifiestos K8s',
        command: 'git pull origin main',
        status: 'running',
        output: 'Ejecutando git pull origin main en backend/config...'
      });
      try {
        const res = await fetch('/api/config_git/pull', {
          method: 'POST',
          headers: getAuthHeaders()
        });
        const data = await res.json();
        if (data.success) {
          updateCommandModalStatus('success', data.message || 'Git pull exitoso.');
        } else {
          updateCommandModalStatus('error', data.message || 'Error en git pull.');
        }
        refreshConfigGitStatus();
        fetchDeploymentVersions();
      } catch (e) {
        updateCommandModalStatus('error', `Error al conectar con servidor para git pull: ${e.message}`);
      }
    }

    async function openConfigGitStatusModal() {
      try {
        const res = await fetch('/api/config_git/status');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('configGitModalTitle').innerText = `📄 Manifiestos K8s: backend/config (${data.branch})`;
        const body = document.getElementById('configGitModalBody');
        
        let filesHtml = '';
        if (data.files && data.files.length > 0) {
          filesHtml = `<div style="max-height:220px; overflow-y:auto; background:#0f172a; border:1px solid #1e293b; border-radius:6px; padding:10px; font-family:ui-monospace, monospace;">` +
            data.files.map(f => `<div style="color:${f.status.includes('M') ? '#f59e0b' : '#34d399'}; margin-bottom:4px;">${f.status} ${f.path}</div>`).join('') +
            `</div>`;
        } else {
          filesHtml = `<p style="color:var(--success);">✅ El repositorio de manifiestos K8s está completamente limpio y sincronizado con <code>origin/${data.branch}</code>.</p>`;
        }

        body.innerHTML = `
          <p>Repositorio: <code>${data.repo_path}</code></p>
          <p>Rama actual: <strong>${data.branch}</strong> | Commits por subir (ahead): <strong>${data.ahead}</strong> | Por bajar (behind): <strong>${data.behind}</strong></p>
          ${filesHtml}
        `;
        document.getElementById('configGitCommitRow').style.display = 'none';
        document.getElementById('btnConfigGitSubmit').style.display = 'none';
        document.getElementById('configGitModal').style.display = 'flex';
      } catch (e) {
        showToast("Error obteniendo estado de git config");
      }
    }

    async function openConfigGitPushModal() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => openConfigGitPushModal(), "Enviar Git Push de manifiestos requiere rol Administrador / DevOps.");
        return;
      }
      try {
        const res = await fetch('/api/config_git/status');
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('configGitModalTitle').innerText = `⬆️ Git Commit & Push: backend/config`;
        const body = document.getElementById('configGitModalBody');
        
        if (data.dirty === 0 && data.ahead === 0) {
          body.innerHTML = `<p style="color:var(--success);">✅ No hay cambios modificados ni commits pendientes por subir en <code>backend/config</code>.</p>`;
          document.getElementById('configGitCommitRow').style.display = 'none';
          document.getElementById('btnConfigGitSubmit').style.display = 'none';
        } else {
          let filesList = (data.files || []).map(f => `<div>${f.status} ${f.path}</div>`).join('');
          body.innerHTML = `
            <p>Se guardarán los cambios y se hará push hacia <code>origin/${data.branch}</code>.</p>
            <p>Archivos a incluir (<strong>${data.dirty}</strong> cambios pendientes, <strong>${data.ahead}</strong> commits previos):</p>
            <div style="max-height:140px; overflow-y:auto; background:#0f172a; border:1px solid #1e293b; border-radius:6px; padding:8px; font-family:ui-monospace, monospace; font-size:11px; margin-bottom:10px;">
              ${filesList || '<em>Ningún archivo sin commitear (subiendo commits locales existentes)</em>'}
            </div>
          `;
          document.getElementById('configGitCommitRow').style.display = (data.dirty > 0) ? 'flex' : 'none';
          document.getElementById('btnConfigGitSubmit').style.display = 'inline-flex';
        }
        document.getElementById('configGitModal').style.display = 'flex';
      } catch (e) {
        showToast("Error preparando Git Push");
      }
    }

    function closeConfigGitModal() {
      document.getElementById('configGitModal').style.display = 'none';
    }

    async function submitConfigGitPush() {
      if (currentUserRole !== 'admin') {
        ensureAdminAuth(() => submitConfigGitPush(), "Enviar Git Push de manifiestos requiere rol Administrador / DevOps.");
        return;
      }
      const msg = document.getElementById('configGitCommitMsg').value.trim() || 'Actualización de manifiestos k8s';
      closeConfigGitModal();
      openCommandModal({
        title: 'Git Commit & Push — backend/config',
        subtitle: 'Manifiestos K8s',
        command: `git commit -m "${msg}" && git push origin main`,
        status: 'running',
        output: 'Realizando commit y push en backend/config...'
      });
      try {
        const res = await fetch('/api/config_git/push', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ commit_message: msg })
        });
        const data = await res.json();
        if (data.success) {
          updateCommandModalStatus('success', data.message || 'Push completado exitosamente.');
        } else {
          updateCommandModalStatus('error', data.message || 'Error en push de manifiestos.');
        }
        refreshConfigGitStatus();
      } catch (e) {
        updateCommandModalStatus('error', `Error enviando push: ${e.message}`);
      }
    }

    // -------------------------------------------------------------------------
    // Modales de Git Auth & Branch Picker
    // -------------------------------------------------------------------------
    async function openGitAuthModal(serviceName, action) {
      if (!ensureDevOrAdminAuth()) return;
      pendingGit = { service: serviceName, action: action };
      document.getElementById('gitAuthTitle').innerText = `Git ${action.toUpperCase()} — ${serviceName}`;

      const stratRow = document.getElementById('gitPullStrategyRow');
      if (stratRow) {
        stratRow.style.display = (action === 'pull') ? 'block' : 'none';
        document.getElementById('gitPullStrategy').value = 'default';
      }

      const pushRow = document.getElementById('gitPushInspectorRow');
      if (pushRow) {
        if (action === 'push') {
          pushRow.style.display = 'block';
          document.getElementById('gitPushBranchBadge').innerText = 'Consultando...';
          document.getElementById('gitPushCommitsStatus').innerHTML = '<span class="spinner" style="width:11px; height:11px; border-width:2px; display:inline-block;"></span> Analizando estado de la rama...';
          document.getElementById('gitPushCommitsList').style.display = 'none';
          document.getElementById('gitPushDirtyWarning').innerHTML = '';

          try {
            const res = await fetch(`/api/service/info?service=${serviceName}&port=0`);
            if (res.ok) {
              const data = await res.json();
              const git = data.git || {};
              const branch = git.branch || 'HEAD';
              const ahead = git.ahead || 0;
              const dirty = git.dirty || 0;
              const commits = git.unpushed_commits || [];
              const dirtyFiles = git.dirty_files || [];

              document.getElementById('gitPushBranchBadge').innerText = `origin/${branch}`;

              if (ahead > 0) {
                document.getElementById('gitPushCommitsStatus').innerHTML = `
                  <span style="color:#34d399; font-weight:700;">⬆️ ${ahead} commit(s) locales listos para subir a GitLab:</span>
                `;
                const listEl = document.getElementById('gitPushCommitsList');
                listEl.style.display = 'block';
                listEl.innerHTML = commits.map(c => `<div>${c}</div>`).join('');
              } else {
                document.getElementById('gitPushCommitsStatus').innerHTML = `
                  <span style="color:#f59e0b; font-weight:700;">⚠️ Sin commits pendientes (ahead: 0).</span>
                  <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">Git no enviará nada nuevo a GitLab ('Everything up-to-date').</div>
                `;
                document.getElementById('gitPushCommitsList').style.display = 'none';
              }

              if (dirty > 0) {
                document.getElementById('gitPushDirtyWarning').innerHTML = `
                  <div style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:6px 8px; margin-top:6px; color:#fca5a5;">
                    <strong>⚠️ Tienes ${dirty} archivo(s) modificados sin commitear.</strong><br>
                    <span>Git Push solo sube commits ya confirmados. Estos archivos <em>NO</em> se subirán a GitLab:</span>
                    <div style="font-family:ui-monospace, monospace; font-size:10px; margin-top:4px; opacity:0.9;">
                      ${dirtyFiles.slice(0, 4).join('<br>')}${dirtyFiles.length > 4 ? '<br>...' : ''}
                    </div>
                  </div>
                `;
              } else {
                document.getElementById('gitPushDirtyWarning').innerHTML = `
                  <div style="color:#34d399; font-size:11px; margin-top:4px;">✅ Árbol de trabajo limpio (sin archivos pendientes de commit).</div>
                `;
              }
            }
          } catch (e) {
            document.getElementById('gitPushCommitsStatus').innerText = 'No se pudo inspeccionar el estado git del servicio.';
          }
        } else {
          pushRow.style.display = 'none';
        }
      }

      const pullRow = document.getElementById('gitPullInspectorRow');
      if (pullRow) {
        if (action === 'pull') {
          pullRow.style.display = 'block';
          document.getElementById('gitPullBranchBadge').innerText = 'Consultando...';
          document.getElementById('gitPullCommitsStatus').innerHTML = '<span class="spinner" style="width:11px; height:11px; border-width:2px; display:inline-block;"></span> Analizando estado remoto...';
          document.getElementById('gitPullCommitsList').style.display = 'none';
          document.getElementById('gitPullDirtyWarning').innerHTML = '';

          try {
            const res = await fetch(`/api/service/info?service=${serviceName}&port=0`);
            if (res.ok) {
              const data = await res.json();
              const git = data.git || {};
              const branch = git.branch || 'HEAD';
              const behind = git.behind || 0;
              const dirty = git.dirty || 0;
              const commits = git.unpulled_commits || [];
              const dirtyFiles = git.dirty_files || [];
              const hasUpstream = git.has_upstream !== false;

              document.getElementById('gitPullBranchBadge').innerText = hasUpstream ? `origin/${branch}` : `origin/${branch} (sin remoto aún)`;

              if (behind > 0) {
                document.getElementById('gitPullCommitsStatus').innerHTML = `
                  <span style="color:#f87171; font-weight:700;">⬇️ Rama desactualizada: ${behind} commit(s) pendientes de bajar desde GitLab:</span>
                `;
                const listEl = document.getElementById('gitPullCommitsList');
                listEl.style.display = 'block';
                listEl.innerHTML = commits.map(c => `<div>${c}</div>`).join('');
              } else {
                document.getElementById('gitPullCommitsStatus').innerHTML = `
                  <span style="color:#34d399; font-weight:700;">✅ Rama al día respecto a GitLab (behind: 0).</span>
                  <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">No hay nuevos commits remotos pendientes ('Already up to date').</div>
                `;
                document.getElementById('gitPullCommitsList').style.display = 'none';
              }

              if (dirty > 0) {
                document.getElementById('gitPullDirtyWarning').innerHTML = `
                  <div style="background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:6px; padding:6px 8px; margin-top:6px; color:#fbbf24;">
                    <strong>⚠️ Tienes ${dirty} archivo(s) locales modificados sin commitear.</strong><br>
                    <span>Hacer pull podría causar conflictos si GitLab modificó los mismos archivos:</span>
                    <div style="font-family:ui-monospace, monospace; font-size:10px; margin-top:4px; opacity:0.9;">
                      ${dirtyFiles.slice(0, 4).join('<br>')}${dirtyFiles.length > 4 ? '<br>...' : ''}
                    </div>
                  </div>
                `;
              } else {
                document.getElementById('gitPullDirtyWarning').innerHTML = `
                  <div style="color:#34d399; font-size:11px; margin-top:4px;">✅ Árbol de trabajo limpio (sin modificaciones locales pendientes).</div>
                `;
              }
            }
          } catch (e) {
            document.getElementById('gitPullCommitsStatus').innerText = 'No se pudo inspeccionar el estado git del servicio.';
          }
        } else {
          pullRow.style.display = 'none';
        }
      }

      document.getElementById('gitAuthModal').style.display = 'flex';
    }
    function closeGitAuthModal() { document.getElementById('gitAuthModal').style.display = 'none'; }

    async function submitGitAuth() {
      if (!ensureDevOrAdminAuth()) return;
      const u = document.getElementById('gitUsername').value.trim();
      const p = document.getElementById('gitPassword').value.trim();
      const save = document.getElementById('gitSaveCreds').checked;
      const pullStrat = document.getElementById('gitPullStrategy') ? document.getElementById('gitPullStrategy').value : 'default';
      const actUpper = pendingGit.action.toUpperCase();
      const svc = pendingGit.service;
      closeGitAuthModal();

      let pullFlags = '';
      if (pullStrat === 'no-ff') pullFlags = ' --no-ff';
      else if (pullStrat === 'merge') pullFlags = ' --no-rebase';
      else if (pullStrat === 'rebase') pullFlags = ' --rebase';
      else if (pullStrat === 'ff-only') pullFlags = ' --ff-only';

      const cmdStr = (pendingGit.action === 'pull')
        ? `git pull${pullFlags}`
        : `git ${pendingGit.action}`;

      openCommandModal({
        title: `Git ${actUpper} — ${svc}`,
        subtitle: `Repositorio: ${svc}`,
        command: cmdStr,
        status: 'running',
        output: `Ejecutando ${cmdStr} en ${svc}...`
      });

      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            action: 'git-action',
            service: svc,
            subaction: pendingGit.action,
            pull_strategy: pullStrat,
            username: u,
            password: p,
            save_credentials: save
          })
        });
        const data = await res.json();
        if (data.success) {
          updateCommandModalStatus('success', data.message || `Git ${actUpper} completado con éxito.`);
        } else {
          updateCommandModalStatus('error', data.message || `Error en Git ${actUpper}.`);
        }
      } catch (err) {
        updateCommandModalStatus('error', `Error de conexión: ${err.message}`);
      }
      fetchStatus();
    }

    async function openBranchPicker(serviceName, port) {
      if (!ensureDevOrAdminAuth()) return;
      pendingBranchService = { name: serviceName, port: port };
      const res = await fetch(`/api/branches?service=${serviceName}`);
      if (!res.ok) return;
      const data = await res.json();

      const sel = document.getElementById('branchSelect');
      sel.innerHTML = '';
      data.branches.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b;
        opt.textContent = b + (b === data.current ? ' (Actual)' : '');
        if (b === data.current) opt.selected = true;
        sel.appendChild(opt);
      });

      document.getElementById('branchModalTitle').innerText = `Cambiar Rama: ${serviceName}`;
      document.getElementById('branchModal').style.display = 'flex';
    }
    function closeBranchModal() { document.getElementById('branchModal').style.display = 'none'; }

    async function submitBranchSwitch() {
      if (!ensureDevOrAdminAuth()) return;
      const branch = document.getElementById('branchSelect').value;
      const autoRestart = document.getElementById('branchAutoRestart').checked;
      const svc = pendingBranchService.name;
      closeBranchModal();

      openCommandModal({
        title: `Git Checkout — ${svc}`,
        subtitle: `Cambiando rama local a '${branch}'`,
        command: `git checkout ${branch}`,
        status: 'running',
        output: `Cambiando rama en ${svc}...`
      });

      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            action: 'checkout-branch',
            service: svc,
            branch: branch,
            port: pendingBranchService.port,
            restart: autoRestart
          })
        });
        const data = await res.json();
        if (data.success) {
          updateCommandModalStatus('success', data.message || `Cambiado a rama '${branch}' con éxito.`);
        } else {
          updateCommandModalStatus('error', data.message || `Error al cambiar de rama a '${branch}'.`);
        }
      } catch (err) {
        updateCommandModalStatus('error', `Error de conexión: ${err.message}`);
      }
      fetchStatus();
    }

    /** Crea una rama nueva en el repo del servicio (git checkout -b). */
    async function submitBranchCreate() {
      if (!ensureDevOrAdminAuth()) return;
      const svc = pendingBranchService.name;
      const nueva = (document.getElementById('branchNuevaNombre').value || '').trim();
      const desde = (document.getElementById('branchSelect').value || '').trim();
      if (!nueva) {
        showToast('⚠️ Escribe el nombre de la rama nueva.');
        return;
      }
      const autoRestart = document.getElementById('branchAutoRestart').checked;
      closeBranchModal();
      openCommandModal({
        title: `Git Crear Rama — ${svc}`,
        subtitle: `Nueva rama '${nueva}' desde '${desde}'`,
        command: `git checkout -b ${nueva} ${desde}`,
        status: 'running',
        output: `Creando rama '${nueva}' en ${svc}...`
      });
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            action: 'create-branch', service: svc, branch: nueva,
            from_branch: desde, port: pendingBranchService.port, restart: autoRestart
          })
        });
        const data = await res.json();
        updateCommandModalStatus(data.success ? 'success' : 'error',
          data.message || (data.success ? 'Rama creada.' : 'No se pudo crear la rama.'));
      } catch (err) {
        updateCommandModalStatus('error', `Error de conexión: ${err.message}`);
      }
      fetchStatus();
    }

    /** Renombra la rama seleccionada (git branch -m). */
    async function submitBranchRename() {
      if (!ensureDevOrAdminAuth()) return;
      const svc = pendingBranchService.name;
      const vieja = (document.getElementById('branchSelect').value || '').trim();
      const nueva = (document.getElementById('branchRenombrar').value || '').trim();
      if (!nueva) {
        showToast('⚠️ Escribe el nombre nuevo de la rama.');
        return;
      }
      if (vieja === nueva) {
        showToast('⚠️ El nombre nuevo es igual al de la rama seleccionada.');
        return;
      }
      closeBranchModal();
      openCommandModal({
        title: `Git Renombrar Rama — ${svc}`,
        subtitle: `'${vieja}' → '${nueva}'`,
        command: `git branch -m ${vieja} ${nueva}`,
        status: 'running',
        output: `Renombrando rama en ${svc}...`
      });
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ action: 'rename-branch', service: svc, old: vieja, new: nueva })
        });
        const data = await res.json();
        updateCommandModalStatus(data.success ? 'success' : 'error',
          data.message || (data.success ? 'Rama renombrada.' : 'No se pudo renombrar la rama.'));
      } catch (err) {
        updateCommandModalStatus('error', `Error de conexión: ${err.message}`);
      }
      fetchStatus();
    }

    async function openServiceMosaicModal(serviceName, port) {
      openCommandModal({
        title: `Logs y Estado: ${serviceName}`,
        subtitle: `Runtime tmux (puerto :${port})`,
        command: `tmux capture-pane -p -t sisper_${serviceName}`,
        status: 'running',
        output: 'Cargando logs en vivo...'
      });
      try {
        const res = await fetch(`/api/services/mosaic?service=${serviceName}&max_lines=25`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const lines = (data.recent_lines || []).join('\n') || '(Sin logs capturados todavía)';
        const status = data.is_standby ? 'error' : (data.status === 'RUNNING' ? 'success' : 'running');
        const header = `[ESTADO: ${data.status} | RUNTIME: ${data.runtime_host} | PID: ${data.pid || 'N/A'} | UPTIME: ${data.uptime_seconds != null ? data.uptime_seconds + 's' : 'N/A'}]\n\n`;
        updateCommandModalStatus(status, header + lines);
      } catch (err) {
        updateCommandModalStatus('error', `Error al consultar logs de ${serviceName}: ${err.message}`);
      }
    }

    let activeFocusedTerm = null;

    async function openFocusedTerminal(serviceName) {
      closeAllCardMenus();

      if (!window.devconsoleTerminal) {
        showToast('ℹ️ Terminal integrada activa en Electron Desktop. Abriendo visor Tilix...');
        await openTilixViewer(serviceName);
        return;
      }

      if (activeFocusedTerm) {
        await closeFocusedTerminal();
      }

      const modal = document.getElementById('focusedTerminalModal');
      const container = document.getElementById('focusedTerminalContainer');
      const title = document.getElementById('focusedTerminalTitle');
      const subtitle = document.getElementById('focusedTerminalSubtitle');
      const badge = document.getElementById('focusedTerminalBadge');

      title.innerText = `Terminal: ${serviceName}`;
      subtitle.innerText = `Adjuntando a tmux (sisper_${serviceName})...`;
      badge.innerText = 'CONECTANDO...';
      badge.style.background = 'rgba(234, 179, 8, 0.2)';
      badge.style.color = '#eab308';
      container.innerHTML = '';
      modal.style.display = 'flex';

      try {
        await cargarXterm();
        if (typeof Terminal === 'undefined') {
          throw new Error('Librería xterm.js no disponible.');
        }

        const term = new Terminal({
          cursorBlink: true,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: 13,
          theme: {
            /* Paleta del tema activo (theme.js / themes.css) */
            ...(window.SisperTheme ? SisperTheme.termTheme() : {
            background: '#0f172a',
            foreground: '#e2e8f0',
            cursor: '#38bdf8',
            selectionBackground: 'rgba(56, 189, 248, 0.3)',
            black: '#0f172a',
            red: '#ef4444',
            green: '#22c55e',
            yellow: '#eab308',
            blue: '#3b82f6',
            magenta: '#a855f7',
            cyan: '#06b6d4',
            white: '#f8fafc',
            brightBlack: '#475569',
            brightRed: '#f87171',
            brightGreen: '#4ade80',
            brightYellow: '#fde047',
            brightBlue: '#60a5fa',
            brightMagenta: '#c084fc',
            brightCyan: '#22d3ee',
            brightWhite: '#ffffff',
            })
          },
        });

        term.open(container);

        const cols = Math.max(40, Math.floor((container.clientWidth - 20) / 9)) || 100;
        const rows = Math.max(10, Math.floor((container.clientHeight - 20) / 17)) || 30;

        const initResult = await window.devconsoleTerminal.init({
          service: serviceName,
          cols,
          rows,
        });

        const termId = initResult.id;

        badge.innerText = 'ACTIVO (tmux)';
        badge.style.background = 'rgba(34, 197, 94, 0.2)';
        badge.style.color = '#22c55e';
        subtitle.innerText = `Conectado a ${initResult.session} (${initResult.cols}x${initResult.rows})`;

        const dataDisposable = term.onData((data) => {
          window.devconsoleTerminal.sendData(termId, data);
        });

        const unsubOutput = window.devconsoleTerminal.onOutput((id, data) => {
          if (id === termId) {
            term.write(data);
          }
        });

        const unsubExit = window.devconsoleTerminal.onExit((id, code, sig) => {
          if (id === termId) {
            badge.innerText = 'DESCONECTADO';
            badge.style.background = 'rgba(239, 68, 68, 0.2)';
            badge.style.color = '#ef4444';
            term.write(`\r\n\x1b[33m[Sesión finalizada (código: ${code ?? 0}, señal: ${sig ?? 'ninguna'})]\x1b[0m\r\n`);
          }
        });

        let resizeTimer = null;
        const resizeObserver = new ResizeObserver((entries) => {
          if (!entries.length) return;
          clearTimeout(resizeTimer);
          resizeTimer = setTimeout(() => {
            if (!term || !term.element) return;
            const newCols = Math.max(40, Math.floor((container.clientWidth - 20) / 9));
            const newRows = Math.max(10, Math.floor((container.clientHeight - 20) / 17));
            try {
              term.resize(newCols, newRows);
              window.devconsoleTerminal.resize(termId, newCols, newRows);
            } catch (_) {}
          }, 100);
        });
        resizeObserver.observe(container);

        activeFocusedTerm = {
          id: termId,
          term,
          serviceName,
          dataDisposable,
          unsubOutput,
          unsubExit,
          resizeObserver,
        };

        term.focus();

      } catch (err) {
        badge.innerText = 'ERROR';
        badge.style.background = 'rgba(239, 68, 68, 0.2)';
        badge.style.color = '#ef4444';
        subtitle.innerText = `Error: ${err.message}`;
        container.innerHTML = `<div style="padding:20px; color:#ef4444; font-family:monospace;">Error iniciando terminal: ${err.message}</div>`;
      }
    }

    async function closeFocusedTerminal() {
      const modal = document.getElementById('focusedTerminalModal');
      if (modal) modal.style.display = 'none';

      if (activeFocusedTerm) {
        const { id, term, dataDisposable, unsubOutput, unsubExit, resizeObserver } = activeFocusedTerm;
        try {
          if (resizeObserver) resizeObserver.disconnect();
          if (dataDisposable && typeof dataDisposable.dispose === 'function') dataDisposable.dispose();
          if (typeof unsubOutput === 'function') unsubOutput();
          if (typeof unsubExit === 'function') unsubExit();
          if (window.devconsoleTerminal && id) {
            await window.devconsoleTerminal.destroy(id);
          }
          if (term && typeof term.dispose === 'function') {
            term.dispose();
          }
        } catch (err) {
          console.warn('[focused-term] Error durante cierre:', err);
        }
        activeFocusedTerm = null;
      }
    }

    async function openTilixViewer(serviceName) {
      closeAllCardMenus();
      showToast(`🖥️ Conectando visor Tilix seguro a ${serviceName}...`);
      try {
        const res = await fetch('/api/tilix/attach_viewer', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ service: serviceName })
        });

        const data = await res.json();
        if (data.success) {
          showToast(`✅ ${data.message}`);
        } else {
          showToast(`❌ ${data.message}`);
        }
      } catch (err) {
        showToast(`❌ Error: ${err.message}`);
      }
    }

    // =========================================================================
    // CONSOLE VIEWPORT — CANONICAL CONSOLE UX (Phase 6S)
    // -------------------------------------------------------------------------
    // Single source of truth for rendering a console viewport, extracted from
    // the reference experience of this application: Kubernetes -> Logs Pro.
    //
    // Consumers:
    //   A. Kubernetes -> Logs Pro      (applyLogFilter -> ConsoleViewport.renderLines)
    //   B. Servicios y Consolas (wall) (renderPanelBody  -> the same renderer)
    //   C. future log viewers
    //
    // There is exactly ONE line renderer and ONE stylesheet for consoles
    // (`.console-line` / `.console-viewport*` in static/css/dashboard.css).
    // =========================================================================

    const ConsoleViewport = {
      /** Bounded DOM: never render the whole ring buffer into a card. */
      MAX_DOM_LINES: 200,

      /** Logs Pro line classification, reused verbatim by the wall. */
      classifyLine(lineText) {
        const lower = String(lineText).toLowerCase();
        if (lower.includes('error') || lower.includes('exception')
            || lower.includes('fatal') || lower.includes('critical')) {
          return 'is-error';
        }
        if (lower.includes('warn') || lower.includes('warning')) return 'is-warn';
        if (lower.includes('info')) return 'is-info';
        return '';
      },

      /**
       * Render log lines to HTML.
       *
       * @param {string[]} lines    raw log lines
       * @param {object}   options
       * @param {string}   options.query    search term (highlighted with <mark>)
       * @param {boolean}  options.filter   when true, drop non-matching lines
       *                                    (Logs Pro behaviour); when false the
       *                                    wall only highlights matches.
       * @param {number}   options.maxLines keep only the newest N lines
       * @returns {{html: string, count: number, total: number}}
       */
      renderLines(lines, options = {}) {
        const query = (options.query || '').trim();
        const doFilter = Boolean(options.filter) && Boolean(query);
        const maxLines = Number(options.maxLines || 0);

        let source = Array.isArray(lines) ? lines : [];
        const total = source.length;
        if (maxLines > 0 && source.length > maxLines) {
          source = source.slice(-maxLines);
        }
        if (doFilter) {
          const qLower = query.toLowerCase();
          source = source.filter((l) => l.toLowerCase().includes(qLower));
        }
        if (source.length === 0) {
          return { html: '', count: 0, total };
        }

        const qRegex = query
          ? new RegExp('(' + escapeRegex(escapeHtml(query)) + ')', 'gi')
          : null;

        const html = source.map((line) => {
          let safe = escapeHtml(line);
          if (qRegex) {
            safe = safe.replace(qRegex, '<mark>$1</mark>');
          }
          const cls = ConsoleViewport.classifyLine(safe);
          return `<div class="console-line${cls ? ' ' + cls : ''}">${safe || '&nbsp;'}</div>`;
        }).join('');

        return { html, count: source.length, total };
      },

      /** True when the viewport is pinned to its newest line. */
      isAtBottom(el, threshold = 30) {
        if (!el) return true;
        return (el.scrollHeight - el.scrollTop - el.clientHeight) < threshold;
      },

      scrollToBottom(el) {
        if (el) el.scrollTop = el.scrollHeight;
      },
    };

    // =========================================================================
    // WORKSPACE OPERACIONAL: SERVICIOS Y CONSOLAS (Phase 6S)
    // Fixed viewport workspace: Logs Pro look & feel, internal scroll only.
    // =========================================================================

    // Presupuesto de repintado por consola.  Reconstruir 200 líneas cuesta
    // ~57-130 ms (medido con CDP), así que pintar a la frecuencia del broker
    // (8 Hz) satura el hilo principal y el muro se queda atrás.  400 ms por
    // panel (~2,5 Hz) es imperceptible en un log y reparte el coste.
    const WALL_PAINT_MS = 400;

    const consoleWorkspace = {
      monitoredServices: new Set(),
      viewMode: 'mosaic',        // 'mosaic' | 'tabs'
      groupMode: 'flat',          // 'flat' | 'grouped'
      density: 'compacto',        // 'comodo' | 'compacto' | 'denso'
      /* 'auto' ajusta las columnas al ancho disponible para que la consola sea
         legible (antes 6 columnas fijas dejaban paneles de 273 px donde las
         líneas de log se partían en dos). */
      gridCols: 'auto',
      gridColsManual: false,      // true en cuanto el usuario elige columnas a mano
      activeTab: null,
      filter: 'all',              // 'all' | 'running' | 'starting' | 'standby' | 'stopped' | 'error'
      categoryFilter: 'all',      // 'all' | 'backend' | 'frontend' | 'worker' | 'consumer' | 'beat' | 'auxiliary'
      searchQuery: '',
      outputSearchQuery: '',
      globalFollow: true,
      followMap: new Map(),       // serviceName -> boolean (default true)
      controlMap: new Map(),      // serviceName -> { id, term, dataDisposable, unsubOutput, unsubExit, resizeObserver }
      buffers: new Map(),         // serviceName -> string[] (ring buffer up to 1000 lines)
      catalogMap: new Map(),      // serviceName -> item metadata
      collapsedGroups: new Set(), // categories collapsed in grouped view
      maximizedService: null,     // serviceName or null
      sidebarCollapsed: false,    // full-width console mode
      lastUpdateMap: new Map(),   // serviceName -> HH:MM:SS of last delta
      /* Frescura de tráfico: instante (epoch s del servidor) de la última línea
         realmente recibida, para delatar servicios en reposo de un vistazo. */
      lastLineTsMap: new Map(),   // serviceName -> epoch s de la última línea
      serverClockOffsetMs: 0,     // Date.now() + offset ≈ reloj del servidor
      /* Revisión monotónica por consola: sube sólo cuando su contenido cambia
         de verdad.  El renderKey la usa para decidir el repintado; sin ella,
         una consola con la última línea en blanco (lo normal en una captura de
         tmux) y más de `tailLines` líneas se quedaba congelada para siempre:
         la clave sólo miraba el número de líneas y la última del recorte. */
      revMap: new Map(),          // serviceName -> número de revisión
      lastPaintMap: new Map(),    // serviceName -> performance.now() del último repintado
      paintTimers: new Map(),     // serviceName -> temporizador de repintado pendiente
      scrollGuardUntil: new Map(),// serviceName -> hasta cuándo ignorar scroll de repintado
      brokerNames: new Set(),     // nombres vivos según el broker (incluye auxiliares)
      /* --- estado por consola (lenguaje del laboratorio) --- */
      filterMap: new Map(),       // serviceName -> filtro de líneas ('' = todas)
      errorsMap: new Map(),       // serviceName -> boolean (solo errores)
      queryMap: new Map(),        // serviceName -> búsqueda con resaltado
      matchIndexMap: new Map(),   // serviceName -> coincidencia activa
      fontMap: new Map(),         // serviceName -> px de letra de esa consola
      wallFontSize: 11,           // px global del muro (control A± de la barra)
      filterAll: '',              // filtro de líneas global (chips del muro)
      errorsAll: false,           // solo errores en todas las consolas
      onlyActive: false,          // muro: mostrar solo consolas con sesión viva
      tailLines: 200,             // líneas visibles por consola
      orderMode: 'manual',        // manual | name | nameDesc | port | type
      orderList: [],              // orden manual (nombres de servicio)
      focusList: [],              // consolas en enfoque (máx. 3)
      focusLayout: 'auto',        // auto | cols | rows | big
      paused: false,              // pausa de actualización del muro
      showAll: true,              // el muro muestra todos los servicios (1:1 con el laboratorio)
      nameFilter: '',             // buscador de microservicios del muro
      wheelActive: null,          // consola que captura la rueda (activada con clic)
      dirtyPanels: new Set(),
      renderScheduled: false,
      visibilityScheduled: false,
      pollTimer: null,
      clockTimer: null,
      sseHealthy: false,          // el SSE entrega instantánea y deltas
      lastWallPoll: 0,            // cuándo se sondeó /api/services/wall por última vez
      eventSource: null,
      isActiveTab: false,
    };

    // -------------------------------------------------------------------------
    // Persistence
    // -------------------------------------------------------------------------
    function loadConsoleWorkspaceStorage() {
      try {
        const saved = localStorage.getItem('sisper_console_workspace');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed.monitored)) {
            consoleWorkspace.monitoredServices = new Set(parsed.monitored);
          }
          if (['mosaic', 'tabs'].includes(parsed.viewMode)) {
            consoleWorkspace.viewMode = parsed.viewMode;
          }
          if (['flat', 'grouped'].includes(parsed.groupMode)) {
            consoleWorkspace.groupMode = parsed.groupMode;
          }
          if (['comodo', 'compacto', 'denso'].includes(parsed.density)) {
            consoleWorkspace.density = parsed.density;
          }
          if (['auto', '1', '2', '3', '4', '5', '6', '7', '8'].includes(parsed.gridCols)) {
            consoleWorkspace.gridCols = parsed.gridCols;
            consoleWorkspace.gridColsManual = parsed.gridColsManual === true;
            /* Migración: quien nunca eligió columnas a mano tenía el 6 fijo
               heredado, que deja los paneles demasiado estrechos. */
            if (!consoleWorkspace.gridColsManual && consoleWorkspace.gridCols === '6') {
              consoleWorkspace.gridCols = 'auto';
            }
          }
          if (parsed.categoryFilter) {
            consoleWorkspace.categoryFilter = parsed.categoryFilter;
          }
          if (typeof parsed.sidebarCollapsed === 'boolean') {
            consoleWorkspace.sidebarCollapsed = parsed.sidebarCollapsed;
          }
          if (parsed.filter) {
            consoleWorkspace.filter = parsed.filter;
          }
          if (parsed.filterMap) consoleWorkspace.filterMap = new Map(Object.entries(parsed.filterMap));
          if (parsed.errorsMap) consoleWorkspace.errorsMap = new Map(Object.entries(parsed.errorsMap));
          if (parsed.fontMap) consoleWorkspace.fontMap = new Map(Object.entries(parsed.fontMap));
          if (typeof parsed.wallFontSize === 'number') consoleWorkspace.wallFontSize = parsed.wallFontSize;
          if (typeof parsed.tailLines === 'number') consoleWorkspace.tailLines = parsed.tailLines;
          if (parsed.orderMode) consoleWorkspace.orderMode = parsed.orderMode;
          if (Array.isArray(parsed.orderList)) consoleWorkspace.orderList = parsed.orderList;
          if (typeof parsed.filterAll === 'string') consoleWorkspace.filterAll = parsed.filterAll;
          if (typeof parsed.errorsAll === 'boolean') consoleWorkspace.errorsAll = parsed.errorsAll;
          if (typeof parsed.onlyActive === 'boolean') consoleWorkspace.onlyActive = parsed.onlyActive;
          if (Array.isArray(parsed.focusList)) consoleWorkspace.focusList = parsed.focusList.slice(0, 3);
          if (parsed.focusLayout) consoleWorkspace.focusLayout = parsed.focusLayout;
          if (parsed.wallV2 !== true) {
            // Migración única al muro 1:1: 6 columnas como el laboratorio.
            consoleWorkspace.gridCols = '6';
            consoleWorkspace.density = 'compacto';
          }
          // El muro 1:1 no tiene conmutador de vista: siempre mosaico plano,
          // así nadie queda atrapado en un modo sin interfaz para volver.
          consoleWorkspace.viewMode = 'mosaic';
          consoleWorkspace.groupMode = 'flat';
        }
      } catch (e) {
        console.warn('[console-workspace] Error loading storage:', e);
      }
    }

    function saveConsoleWorkspaceStorage() {
      try {
        const data = {
          monitored: Array.from(consoleWorkspace.monitoredServices),
          viewMode: consoleWorkspace.viewMode,
          groupMode: consoleWorkspace.groupMode,
          density: consoleWorkspace.density,
          gridCols: consoleWorkspace.gridCols,
          gridColsManual: consoleWorkspace.gridColsManual,
          categoryFilter: consoleWorkspace.categoryFilter,
          filter: consoleWorkspace.filter,
          sidebarCollapsed: consoleWorkspace.sidebarCollapsed,
          filterMap: Object.fromEntries(consoleWorkspace.filterMap || new Map()),
          errorsMap: Object.fromEntries(consoleWorkspace.errorsMap || new Map()),
          fontMap: Object.fromEntries(consoleWorkspace.fontMap || new Map()),
          wallFontSize: consoleWorkspace.wallFontSize,
          tailLines: consoleWorkspace.tailLines,
          orderMode: consoleWorkspace.orderMode,
          orderList: consoleWorkspace.orderList,
          filterAll: consoleWorkspace.filterAll,
          errorsAll: consoleWorkspace.errorsAll,
          onlyActive: consoleWorkspace.onlyActive,
          focusList: consoleWorkspace.focusList,
          focusLayout: consoleWorkspace.focusLayout,
          wallV2: true,
        };
        localStorage.setItem('sisper_console_workspace', JSON.stringify(data));
      } catch (e) {
        console.warn('[console-workspace] Error saving storage:', e);
      }
    }

    // -------------------------------------------------------------------------
    // ANSI -> safe HTML (XSS sanitised; shared by every console viewport)
    // -------------------------------------------------------------------------
    function ansiToHtml(rawText) {
      if (!rawText) return '';
      let text = escapeHtml(rawText);
      const ansiRegex = /\x1b\[([0-9;]*)m/g;
      let openSpan = false;
      text = text.replace(ansiRegex, (match, p1) => {
        if (!p1 || p1 === '0') {
          const closing = openSpan ? '</span>' : '';
          openSpan = false;
          return closing;
        }
        const codes = p1.split(';').map(c => parseInt(c, 10));
        let styles = [];
        for (const code of codes) {
          if (code === 1) styles.push('font-weight:bold;');
          else if (code === 30) styles.push('color:#64748b;');
          else if (code === 31) styles.push('color:#ef4444;');
          else if (code === 32) styles.push('color:#22c55e;');
          else if (code === 33) styles.push('color:#eab308;');
          else if (code === 34) styles.push('color:#3b82f6;');
          else if (code === 35) styles.push('color:#a855f7;');
          else if (code === 36) styles.push('color:#06b6d4;');
          else if (code === 37) styles.push('color:#f8fafc;');
          else if (code === 90) styles.push('color:#94a3b8;');
          else if (code === 91) styles.push('color:#f87171;');
          else if (code === 92) styles.push('color:#4ade80;');
          else if (code === 93) styles.push('color:#fde047;');
          else if (code === 94) styles.push('color:#60a5fa;');
          else if (code === 95) styles.push('color:#c084fc;');
          else if (code === 96) styles.push('color:#22d3ee;');
          else if (code === 97) styles.push('color:#ffffff;');
        }
        const closePrev = openSpan ? '</span>' : '';
        openSpan = true;
        return `${closePrev}<span style="${styles.join(' ')}">`;
      });
      if (openSpan) text += '</span>';
      return text;
    }

    // -------------------------------------------------------------------------
    // Service classification
    // -------------------------------------------------------------------------
    function getServiceCategory(svc) {
      if (svc.category) return svc.category;
      const name = svc.name || '';
      if (name.includes('worker') || name.includes('celery')) return 'worker';
      if (name.includes('consumer') || name.includes('rabbit')) return 'consumer';
      if (name.includes('beat')) return 'beat';
      if (name.startsWith('mf_')) return 'frontend';
      if (name.startsWith('ms_')) return 'backend';
      return 'auxiliary';
    }

    function getServiceFramework(category) {
      switch (category) {
        case 'backend': return 'Backend (Django)';
        case 'frontend': return 'Frontend (Webpack)';
        case 'worker': return 'Worker (Celery)';
        case 'consumer': return 'Consumer (RabbitMQ)';
        case 'beat': return 'Scheduler (Celery Beat)';
        default: return 'Auxiliar';
      }
    }

    function getServiceRuntimeTag(category) {
      switch (category) {
        case 'backend': return 'Python 3.12 • Django 5.2';
        case 'frontend': return 'Node 20.11 • Webpack 5.89';
        case 'worker': return 'Python 3.12 • Celery 5.3';
        case 'consumer': return 'Python 3.12 • RabbitMQ';
        case 'beat': return 'Python 3.12 • Celery Beat';
        default: return 'Runtime • Host';
      }
    }

    /** Short type badge for the console header (no duplicated metadata). */
    function getServiceTypeBadge(category) {
      switch (category) {
        case 'backend': return 'backend';
        case 'frontend': return 'frontend';
        case 'worker': return 'worker';
        case 'consumer': return 'consumer';
        case 'beat': return 'beat';
        default: return 'aux';
      }
    }

    function getAllServicesList() {
      const map = new Map();
      if (globalData) {
        (globalData.backend || []).forEach(s => map.set(s.name, { ...s, category: 'backend' }));
        (globalData.frontend || []).forEach(s => map.set(s.name, { ...s, category: 'frontend' }));
      }
      for (const [name, catItem] of consoleWorkspace.catalogMap.entries()) {
        if (!map.has(name)) {
          map.set(name, {
            name: catItem.name || name,
            port: catItem.port || '',
            category: catItem.category || getServiceCategory(catItem),
            online: catItem.status === 'RUNNING',
            status: catItem.status || 'STOPPED',
            git: { branch: catItem.branch || 'develop' },
          });
        } else {
          const existing = map.get(name);
          if (catItem.status) {
            existing.status = catItem.status;
            existing.online = (catItem.status === 'RUNNING');
          }
          if (catItem.port && !existing.port) existing.port = catItem.port;
          if (catItem.category) existing.category = catItem.category;
        }
      }
      return Array.from(map.values());
    }

    /** Canonical status normalisation used by filters, dots and badges. */
    function getServiceStatusState(svc) {
      if (!svc) return 'stopped';
      if (svc.status === 'ERROR' || svc.status === 'FAILED') return 'error';
      if (svc.is_standby || svc.status === 'STANDBY') return 'standby';
      if (svc.status === 'STARTING') return 'starting';
      if (svc.online || svc.status === 'RUNNING') return 'running';
      return 'stopped';
    }

    const CONSOLE_STATUS_LABEL = {
      running: 'Activo',
      starting: 'Iniciando',
      standby: 'Standby',
      stopped: 'Detenido',
      error: 'Error',
    };

    function updateLiveClock() {
      const now = new Date();
      const options = {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      };
      const str = now.toLocaleDateString('es-ES', options).replace(',', '');
      const clockText = `🕒 ${str}`;
      const elem = document.getElementById('consoleClock');
      if (elem) elem.innerText = clockText;
      // Los indicadores "hace Ns" del muro envejecen con el reloj, no con los datos.
      if (consoleWorkspace.isActiveTab) refreshWallFreshness();
    }

    function updateRailCounters() {
      const railCount = document.getElementById('consoleRailCount');
      if (railCount) railCount.innerText = `${consoleWorkspace.monitoredServices.size} consolas`;
    }

    // -------------------------------------------------------------------------
    // Sidebar: compact one-line service rows (navigation / control only)
    // -------------------------------------------------------------------------

    /**
     * Prefijo común que comparte la MAYORÍA de un conjunto de nombres.
     *
     * Se calcula por mayoría y no como el prefijo común de *todos*: basta un
     * único nombre atípico —una sesión huérfana dejada por una prueba, un
     * servicio con otra convención— para que el prefijo común del grupo entero
     * se derrumbe y la abreviatura deje de servir precisamente para los demás.
     */
    function majorityCommonPrefix(names, ratio = 0.6) {
      if (!names || names.length < 2) return '';
      const threshold = Math.ceil(names.length * ratio);
      const maxLen = Math.min(...names.map(n => n.length));
      let best = '';

      for (let len = 1; len <= maxLen; len++) {
        const counts = new Map();
        for (const n of names) {
          const part = n.slice(0, len);
          counts.set(part, (counts.get(part) || 0) + 1);
        }
        let winner = '';
        let winnerCount = 0;
        for (const [part, count] of counts) {
          if (count > winnerCount) { winner = part; winnerCount = count; }
        }
        if (winnerCount >= threshold) best = winner;
        else break;
      }

      // Cortar en el último separador para no partir una palabra por la mitad.
      const cut = Math.max(
        best.lastIndexOf('_'), best.lastIndexOf('-'), best.lastIndexOf('.')
      );
      return cut > 0 ? best.slice(0, cut + 1) : '';
    }

    /**
     * Etiquetas cortas y distinguibles para una lista de nombres de servicio.
     *
     * En una barra lateral angosta el nombre completo se recorta por CSS y todas
     * las filas terminan mostrando el mismo texto (`ms_sisper_...`), que es la
     * peor forma de truncar: esconde justo la parte que distingue.  Aquí se
     * agrupa por primer segmento —dato real de los nombres, sin asumir ninguna
     * convención— y se recorta el prefijo común de cada grupo, de modo que la
     * fila muestre sólo lo distintivo.  El nombre completo sigue disponible en
     * el atributo `title` y en la cabecera del panel de consola.
     */
    function buildShortServiceLabels(names) {
      const groups = new Map();
      names.forEach(n => {
        const key = String(n).split(/[_\-.]/)[0] || '';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(n);
      });

      const labels = new Map();
      groups.forEach(groupNames => {
        const prefix = majorityCommonPrefix(groupNames);
        groupNames.forEach(n => labels.set(n, n.slice(prefix.length) || n));
      });

      // Si dos grupos quedaran con la misma etiqueta, se antepone el prefijo
      // del grupo para desambiguar en lugar de dejar filas idénticas.
      const repeats = new Map();
      labels.forEach(v => repeats.set(v, (repeats.get(v) || 0) + 1));
      labels.forEach((v, k) => {
        if (repeats.get(v) > 1) {
          labels.set(k, `${String(k).split(/[_\-.]/)[0]}:${v}`);
        }
      });

      return labels;
    }

    function renderConsoleSidebarServices() {
      const listContainer = document.getElementById('consoleSvcList');
      if (!listContainer) return;
      /* El panel lateral de servicios está RETIRADO del muro: sigue en el DOM
         (para no romper las referencias) pero oculto por CSS, así que pintarlo
         era trabajo tirado en cada actualización de servicios.  Si algún día se
         vuelve a mostrar, hay que llamar a esta función al hacerlo visible. */
      if (listContainer.offsetParent === null) return;
      const all = getAllServicesList();
      const shortLabels = buildShortServiceLabels(all.map(s => s.name));
      const q = (consoleWorkspace.searchQuery || '').toLowerCase();
      const catFilter = consoleWorkspace.categoryFilter;
      const stateFilter = consoleWorkspace.filter;

      let countBackend = 0, countFrontend = 0, countWorker = 0, countConsumer = 0,
        countBeat = 0, countAuxiliary = 0;
      all.forEach(s => {
        switch (getServiceCategory(s)) {
          case 'backend': countBackend += 1; break;
          case 'frontend': countFrontend += 1; break;
          case 'worker': countWorker += 1; break;
          case 'consumer': countConsumer += 1; break;
          case 'beat': countBeat += 1; break;
          default: countAuxiliary += 1;
        }
      });

      const catSelect = document.getElementById('consoleCategorySelect');
      if (catSelect) {
        const labels = {
          all: `Todos (${all.length})`,
          backend: `Backend (${countBackend})`,
          frontend: `Frontend (${countFrontend})`,
          worker: `Workers (${countWorker})`,
          consumer: `Consumers (${countConsumer})`,
          beat: `Beat (${countBeat})`,
          auxiliary: `Auxiliares (${countAuxiliary})`,
        };
        Array.from(catSelect.options).forEach((opt) => {
          if (labels[opt.value]) opt.textContent = labels[opt.value];
        });
        if (catSelect.value !== catFilter) catSelect.value = catFilter;
      }

      const stateSelect = document.getElementById('consoleFilterSelect');
      if (stateSelect && stateSelect.value !== stateFilter) stateSelect.value = stateFilter;

      const filtered = all.filter(s => {
        const cat = getServiceCategory(s);
        if (catFilter !== 'all' && cat !== catFilter) return false;
        const matchesQuery = !q || s.name.toLowerCase().includes(q) || String(s.port || '').includes(q);
        if (!matchesQuery) return false;
        const state = getServiceStatusState(s);
        if (stateFilter === 'all') return true;
        return state === stateFilter;
      });

      const countBadge = document.getElementById('consoleSvcCount');
      if (countBadge) countBadge.innerText = `${filtered.length} / ${all.length}`;

      listContainer.innerHTML = '';
      const rows = filtered.map((s) => {
        const isMonitored = consoleWorkspace.monitoredServices.has(s.name);
        const state = getServiceStatusState(s);
        const label = CONSOLE_STATUS_LABEL[state] || 'Detenido';
        const isRunning = state === 'running';
        const row = document.createElement('div');
        row.className = `console-svc-card ${isMonitored ? 'is-monitored' : ''}`;
        row.dataset.service = s.name;
        row.title = `${s.name}${s.port ? ' :' + s.port : ''} · ${label}`;
        row.innerHTML = `
          <span class="console-svc-status-dot ${state}" title="${escapeHtml(label)}"></span>
          <div class="console-svc-header-row" data-action="toggle-monitor" data-service="${escapeHtml(s.name)}">
            <div class="console-svc-title-part">
              <input type="checkbox" class="console-svc-cb" data-action="toggle-monitor" data-service="${escapeHtml(s.name)}" ${isMonitored ? 'checked' : ''} title="Monitorear consola">
              <span class="console-svc-name" title="${escapeHtml(s.name)}">${escapeHtml(shortLabels.get(s.name) || s.name)}</span>
              ${s.port ? `<span class="console-svc-port">:${escapeHtml(s.port)}</span>` : ''}
            </div>
          </div>
          <div class="console-svc-actions-row">
            ${isRunning
              ? `<button class="console-svc-btn" data-action="quick-restart" data-service="${escapeHtml(s.name)}" data-port="${escapeHtml(s.port || 0)}" title="Reiniciar servicio">⟳</button>`
              : `<button class="console-svc-btn btn-start" data-action="quick-start" data-service="${escapeHtml(s.name)}" data-port="${escapeHtml(s.port || 0)}" title="Iniciar servicio">▶</button>`}
            ${isRunning ? `<button class="console-svc-btn btn-stop" data-action="quick-stop" data-service="${escapeHtml(s.name)}" title="Detener servicio">⏹</button>` : ''}
            <button class="console-svc-btn btn-more" data-action="open-detail" data-service="${escapeHtml(s.name)}" data-port="${escapeHtml(s.port || 0)}" title="Detalles del servicio">⋮</button>
          </div>
        `;
        return row;
      });
      rows.forEach((r) => listContainer.appendChild(r));

      const activeRunningCount = all.filter(s => getServiceStatusState(s) === 'running').length;
      const summaryElem = document.getElementById('consoleSummaryCounts');
      if (summaryElem) {
        summaryElem.innerText = `${consoleWorkspace.monitoredServices.size} consolas · ${activeRunningCount} activos`;
      }
      updateRailCounters();
    }

    // -------------------------------------------------------------------------
    // Console card: Logs Pro viewport with bounded height and internal scroll
    // -------------------------------------------------------------------------
    function getPanelPort(svc) {
      const catItem = consoleWorkspace.catalogMap.get(svc);
      if (catItem && catItem.port) return String(catItem.port);
      const found = getAllServicesList().find(s => s.name === svc);
      return found && found.port ? String(found.port) : '';
    }

    /** Newest `MAX_DOM_LINES` lines only: buffer and DOM are different things. */
    function linesForPanel(svc) {
      const buf = consoleWorkspace.buffers.get(svc) || [];
      const tope = consoleWorkspace.tailLines || ConsoleViewport.MAX_DOM_LINES;
      return buf.length > tope ? buf.slice(-tope) : buf;
    }

    // =========================================================================
    // Muro de consolas — utilidades por consola (lenguaje del laboratorio)
    // =========================================================================
    const CW_FONT_MIN = 9, CW_FONT_MAX = 24;

    /** Botón de control dentro del menú: conserva el estilo y la etiqueta. */
    function updateControlButton(svc, isControl) {
      const btn = document.getElementById(`console-btn-ctrl-${svc}`);
      if (!btn) return;
      btn.dataset.action = isControl ? 'exit-control' : 'take-control';
      btn.title = isControl ? 'Volver a modo monitor (lectura)' : 'Tomar control interactivo (xterm)';
      const icon = btn.querySelector('.k');
      if (icon) icon.textContent = isControl ? '👁' : '🎮';
      btn.innerHTML = `<span class="k">${isControl ? '👁' : '🎮'}</span>${isControl ? 'Volver a modo monitor' : 'Tomar control (xterm)'}`;
    }

    function closePanelMenus(except) {
      document.querySelectorAll('.cw-menu.open').forEach((m) => {
        if (m === except) return;
        m.classList.remove('open');
        m.style.cssText = '';
      });
    }

    function refreshPanelControls(svc) {
      const filtro = consoleWorkspace.filterMap.get(svc) || '';
      const soloErrores = consoleWorkspace.errorsMap.get(svc) === true;
      const esMax = consoleWorkspace.maximizedService === svc;
      const menu = document.getElementById(`console-menu-${svc}`);
      if (menu) {
        menu.querySelectorAll('.cw-chip').forEach((c) => c.classList.toggle('on', (c.dataset.filter || '') === filtro));
        const errBtn = menu.querySelector('[data-action="panel-errors"]');
        if (errBtn) errBtn.classList.toggle('on', soloErrores);
        /* Sólo se reescribe si la etiqueta cambió: esto corre en cada refresco de
           estado (361 veces en 20 s medidos) y reescribir el innerHTML destruye y
           recrea el nodo hijo cada vez. */
        const maxBtn = menu.querySelector('[data-action="toggle-maximize"]');
        if (maxBtn) {
          const txt = esMax ? 'Restaurar panel' : 'Maximizar panel';
          if (maxBtn.dataset.txt !== txt) {
            maxBtn.innerHTML = `<span class="k">⛶</span>${txt}`;
            maxBtn.dataset.txt = txt;
          }
        }
        const enfBtn = menu.querySelector('[data-action="panel-enfoque"]');
        const marcada = consoleWorkspace.focusList.includes(svc);
        if (enfBtn) {
          const txt = marcada ? 'Quitar de Enfoque' : 'Añadir a Enfoque';
          if (enfBtn.dataset.txt !== txt) {
            enfBtn.innerHTML = `<span class="k">◎</span>${txt}`;
            enfBtn.dataset.txt = txt;
          }
        }
        const panelEl = document.getElementById(`console-panel-${svc}`);
        if (panelEl) panelEl.classList.toggle('is-enfoque', marcada);
        const arranque = menu.querySelector('[data-action="quick-start"]');
        const parada = menu.querySelector('[data-action="quick-stop"]');
        const catItem = consoleWorkspace.catalogMap.get(svc) || { name: svc };
        const corriendo = getServiceStatusState(catItem) === 'running';
        if (arranque) arranque.hidden = corriendo;
        if (parada) parada.hidden = !corriendo;
        const estado = menu.querySelector('.cw-mh-state');
        if (estado) {
          estado.textContent = CONSOLE_STATUS_LABEL[getServiceStatusState(catItem)] || 'Detenido';
          estado.className = 'cw-mh-state ' + (corriendo ? 'running' : 'stopped');
        }
      }
      const label = document.getElementById(`console-filterlabel-${svc}`);
      if (label) label.textContent = filtro || (soloErrores ? 'solo errores' : '');
      updateControlButton(svc, consoleWorkspace.controlMap.has(svc));
    }

    function togglePanelMenu(svc) {
      const menu = document.getElementById(`console-menu-${svc}`);
      const btn = document.getElementById(`console-menu-btn-${svc}`);
      if (!menu || !btn) return;
      const abrir = !menu.classList.contains('open');
      closePanelMenus();
      if (!abrir) return;
      refreshPanelControls(svc);
      menu.classList.add('open');
      const r = btn.getBoundingClientRect();
      const mr = menu.getBoundingClientRect();
      const vw = window.innerWidth, vh = window.innerHeight;
      const ancho = Math.max(mr.width, 252);
      let left = Math.min(r.right - ancho, vw - ancho - 8);
      if (left < 8) left = 8;
      let top = r.bottom + 4;
      if (top + mr.height > vh - 8) top = Math.max(8, vh - 8 - mr.height);
      menu.style.position = 'fixed';
      menu.style.left = left + 'px';
      menu.style.top = top + 'px';
      menu.style.maxHeight = Math.min(mr.height, vh - 16) + 'px';
    }

    function actualizarContadorBusqueda(svc, lines, query) {
      const el = document.getElementById(`console-count-${svc}`);
      if (!el) return;
      if (!query) { el.textContent = ''; delete el.dataset.total; return; }
      const q = query.toLowerCase();
      let total = 0;
      for (let i = 0; i < lines.length; i++) {
        const low = lines[i].toLowerCase();
        let at = low.indexOf(q);
        while (at !== -1) { total++; at = low.indexOf(q, at + q.length); }
      }
      el.dataset.total = String(total);
      if (!total) { el.textContent = '0/0'; return; }
      const idx = Math.min(consoleWorkspace.matchIndexMap.get(svc) || 0, total - 1);
      consoleWorkspace.matchIndexMap.set(svc, idx);
      el.textContent = `${idx + 1}/${total}`;
    }

    function panelSearchNav(svc, dir) {
      const el = document.getElementById(`console-count-${svc}`);
      const total = parseInt((el && el.dataset.total) || '0', 10);
      if (!total) return;
      const idx = ((consoleWorkspace.matchIndexMap.get(svc) || 0) + dir + total) % total;
      consoleWorkspace.matchIndexMap.set(svc, idx);
      renderPanelBody(svc, { force: true });
      const body = document.getElementById(`console-monitor-body-${svc}`);
      const marcas = body ? body.querySelectorAll('mark') : [];
      if (marcas[idx]) marcas[idx].scrollIntoView({ block: 'center' });
    }

    function setPanelFont(svc, size) {
      size = Math.max(CW_FONT_MIN, Math.min(CW_FONT_MAX, Math.round(size)));
      consoleWorkspace.fontMap.set(svc, size);
      const body = document.getElementById(`console-monitor-body-${svc}`);
      if (body) body.style.fontSize = size + 'px';
      const el = document.getElementById(`console-font-${svc}`);
      if (el) el.textContent = size + ' px';
      saveConsoleWorkspaceStorage();
      showToast(`🔠 ${svc}: letra ${size} px`);
    }

    function setWallFont(size) {
      size = Math.max(CW_FONT_MIN, Math.min(CW_FONT_MAX, Math.round(size)));
      consoleWorkspace.wallFontSize = size;
      const label = document.getElementById('consoleWallFont');
      if (label) label.textContent = size + ' px';
      consoleWorkspace.fontMap.clear();
      consoleWorkspace.monitoredServices.forEach((svc) => {
        const body = document.getElementById(`console-monitor-body-${svc}`);
        if (body) body.style.fontSize = size + 'px';
        const el = document.getElementById(`console-font-${svc}`);
        if (el) el.textContent = size + ' px';
      });
      saveConsoleWorkspaceStorage();
      showToast(`🔠 Letra de todas las consolas: ${size} px`);
    }

    /** Orden efectivo del muro: manual (arrastre) o por criterio. */
    function wallOrder(allNames) {
      const base = consoleWorkspace.orderList.length
        ? consoleWorkspace.orderList.filter((n) => allNames.includes(n)).concat(allNames.filter((n) => !consoleWorkspace.orderList.includes(n)))
        : allNames.slice();
      const modo = consoleWorkspace.orderMode;
      if (modo === 'manual') return base;
      const cat = (n) => consoleWorkspace.catalogMap.get(n) || { name: n };
      const puerto = (n) => parseInt(cat(n).port || getPanelPort(n) || 0, 10);
      const tipo = (n) => (getServiceCategory(cat(n)) || '');
      const lista = base.slice();
      if (modo === 'name') lista.sort((a, b) => a.localeCompare(b));
      else if (modo === 'nameDesc') lista.sort((a, b) => b.localeCompare(a));
      else if (modo === 'port') lista.sort((a, b) => puerto(a) - puerto(b));
      else if (modo === 'type') lista.sort((a, b) => tipo(a) === tipo(b) ? a.localeCompare(b) : tipo(a).localeCompare(tipo(b)));
      return lista;
    }

    /** Mueve una consola delante/detrás de otra y persiste el orden manual. */
    function moverConsola(from, to, despues) {
      if (!from || !to || from === to) return;
      const grid = document.getElementById('consoleMosaicGrid');
      if (!grid) return;
      const nombres = Array.from(grid.querySelectorAll('.console-panel')).map((p) => p.dataset.service);
      if (!consoleWorkspace.orderList.length) consoleWorkspace.orderList = nombres;
      const lista = consoleWorkspace.orderList.filter((n) => n !== from);
      let idx = lista.indexOf(to);
      if (idx === -1) idx = lista.length - 1;
      lista.splice(idx + (despues ? 1 : 0), 0, from);
      consoleWorkspace.orderList = lista;
      consoleWorkspace.orderMode = 'manual';
      const sel = document.getElementById('consoleSortSelect');
      if (sel) sel.value = 'manual';
      saveConsoleWorkspaceStorage();
      renderConsoleStage();
      showToast(`↔ ${from} movida ${despues ? 'después' : 'antes'} de ${to}`);
    }

    /** Refleja el estado de pausa en la barra del muro. */
    function applyWallPauseUi() {
      const btn = document.getElementById('btnWallPause');
      if (btn) {
        btn.classList.toggle('on', consoleWorkspace.paused);
        btn.innerText = consoleWorkspace.paused ? '▶ Reanudar' : 'Ⅱ Pausar';
      }
      const ind = document.getElementById('consoleLiveIndicator');
      if (ind) ind.innerHTML = consoleWorkspace.paused ? '<span class="dot"></span> En pausa' : '<span class="dot"></span> En vivo';
    }

    /** Muestra todas las consolas del catálogo (estado inicial 1:1). */
    function mostrarTodasLasConsolas() {
      const todas = (globalData.backend || []).concat(globalData.frontend || []).map((s) => s.name);
      const catalogo = Array.from(consoleWorkspace.catalogMap.keys());
      const nombres = todas.length ? todas : catalogo;
      nombres.forEach((n) => consoleWorkspace.monitoredServices.add(n));
      consoleWorkspace.orderList = [];
      saveConsoleWorkspaceStorage();
      renderConsoleSidebarServices();
      renderConsoleStage();
    }

    /** El muro del laboratorio muestra todos los servicios, no una selección. */
    function entrandoAlMuro() {
      if (!consoleWorkspace.showAll) return;
      const base = (globalData.backend || []).concat(globalData.frontend || []).map((s) => s.name);
      const baseSet = new Set(base);
      /* El catálogo del broker incluye las consolas AUXILIARES (consumer, worker,
         beat, shell), que no están en `globalData`.  Sin unirlas, lanzar un
         RabbitMQ/Celery no aparecía nunca en el muro. */
      const nombres = base.concat(Array.from(consoleWorkspace.catalogMap.keys()));
      let nuevas = 0;
      nombres.forEach((n) => { if (n && !consoleWorkspace.monitoredServices.has(n)) { consoleWorkspace.monitoredServices.add(n); nuevas++; } });
      /* Y al revés: una auxiliar que ya no existe en el broker no debe dejar una
         tarjeta fantasma.  Los servicios del catálogo base nunca se quitan. */
      let quitadas = 0;
      if (consoleWorkspace.brokerNames.size) {
        Array.from(consoleWorkspace.monitoredServices).forEach((n) => {
          if (!baseSet.has(n) && !consoleWorkspace.brokerNames.has(n)) { consoleWorkspace.monitoredServices.delete(n); quitadas++; }
        });
        if (quitadas) {
          consoleWorkspace.focusList = consoleWorkspace.focusList.filter((n) => consoleWorkspace.monitoredServices.has(n));
          if (consoleWorkspace.maximizedService && !consoleWorkspace.monitoredServices.has(consoleWorkspace.maximizedService)) {
            consoleWorkspace.maximizedService = null;
          }
        }
      }
      if (nuevas || quitadas) {
        saveConsoleWorkspaceStorage();
        renderConsoleSidebarServices();
        /* Un servicio que aparece (p. ej. recién lanzado desde Microservicios)
           debe tener ya su tarjeta en el muro: antes sólo se pintaba al azar de
           otra acción, y parecía que las dos pestañas no se hablaban. */
        renderConsoleStage();
      }
    }

    function createConsolePanelElement(svc) {
      const panel = document.createElement('div');
      panel.className = 'console-panel';
      panel.id = `console-panel-${svc}`;
      panel.dataset.service = svc;

      const isControl = consoleWorkspace.controlMap.has(svc);
      const cat = getServiceCategory({ name: svc });
      const typeBadge = getServiceTypeBadge(cat);
      const runtimeTagStr = getServiceRuntimeTag(cat);
      const port = getPanelPort(svc);
      const catItem = consoleWorkspace.catalogMap.get(svc) || {};
      const state = getServiceStatusState(catItem.name ? catItem : { name: svc });
      const label = CONSOLE_STATUS_LABEL[state] || 'Detenido';

      const isRunning = state === 'running';
      const filtro = consoleWorkspace.filterMap.get(svc) || '';
      const soloErrores = consoleWorkspace.errorsMap.get(svc) === true;
      const fontSize = consoleWorkspace.fontMap.get(svc) || consoleWorkspace.wallFontSize;
      const estadoClase = state === 'running' ? 'running' : (state === 'stopped' ? 'stopped' : 'starting');

      panel.innerHTML = `
        <div class="console-panel-header">
          <span class="console-panel-dot ${estadoClase}" id="console-status-dot-${escapeHtml(svc)}" title="${escapeHtml(label)}"></span>
          <div class="console-panel-left">
            <span class="console-panel-name" title="${escapeHtml(svc)}">${escapeHtml(svc)}</span>
            ${port ? `<span class="console-panel-port">:${escapeHtml(port)}</span>` : ''}
          </div>
          <div class="console-panel-tools">
            <button class="console-tool-btn" data-action="panel-menu" data-service="${escapeHtml(svc)}" id="console-menu-btn-${escapeHtml(svc)}" title="Acciones y filtros de esta consola" aria-haspopup="true">⋯</button>
          </div>
          <div class="cw-menu" id="console-menu-${escapeHtml(svc)}" role="menu">
            <div class="cw-menu-head">
              <span class="cw-mh-name">${escapeHtml(svc)}</span>
              ${port ? `<span class="cw-mh-port">:${escapeHtml(port)}</span>` : ''}
              <span class="cw-mh-state ${estadoClase}" id="console-menu-state-${escapeHtml(svc)}">${escapeHtml(label)}</span>
            </div>
            <button data-action="panel-search" data-service="${escapeHtml(svc)}"><span class="k">⌕</span>Buscar en esta consola</button>
            <button data-action="panel-errors" data-service="${escapeHtml(svc)}" class="${soloErrores ? 'on' : ''}"><span class="k">⚠</span>Solo errores<span class="tick">✓</span></button>
            <div class="cw-role-sep"></div>
            <div class="cw-role-title">Servicio</div>
            <button data-action="quick-start" data-service="${escapeHtml(svc)}" data-port="${escapeHtml(port || 0)}" ${isRunning ? 'hidden' : ''}><span class="k">▶</span>Iniciar servicio</button>
            <button data-action="quick-stop" data-service="${escapeHtml(svc)}" ${isRunning ? '' : 'hidden'}><span class="k">■</span>Parar servicio</button>
            <button data-action="quick-restart" data-service="${escapeHtml(svc)}" data-port="${escapeHtml(port || 0)}"><span class="k">↻</span>Reiniciar servicio</button>
            <div class="cw-role-sep"></div>
            <div class="cw-role-title">Panel</div>
            <button data-action="panel-enfoque" data-service="${escapeHtml(svc)}"><span class="k">◎</span>${consoleWorkspace.focusList.includes(svc) ? 'Quitar de Enfoque' : 'Añadir a Enfoque'}</button>
            <button data-action="toggle-maximize" data-service="${escapeHtml(svc)}"><span class="k">⛶</span>${consoleWorkspace.maximizedService === svc ? 'Restaurar panel' : 'Maximizar panel'}</button>
            <button data-action="clear-panel" data-service="${escapeHtml(svc)}"><span class="k">⌫</span>Limpiar salida</button>
            <div class="cw-role-sep"></div>
            <div class="cw-role-title">Letra de esta consola</div>
            <div class="cw-font">
              <button data-action="font-down" data-service="${escapeHtml(svc)}" title="Letra más pequeña">A−</button>
              <span class="cw-fv" id="console-font-${escapeHtml(svc)}">${fontSize} px</span>
              <button data-action="font-up" data-service="${escapeHtml(svc)}" title="Letra más grande">A+</button>
            </div>
            <div class="cw-role-sep"></div>
            <div class="cw-role-title">Filtro de líneas</div>
            <div class="cw-chips">
              ${['ERROR', 'WARN', 'INFO', 'GET', 'POST', 'PUT', 'DELETE'].map((f) => `<button class="cw-chip ${filtro === f ? 'on' : ''}" data-action="panel-filter" data-service="${escapeHtml(svc)}" data-filter="${f}">${f}</button>`).join('')}
              <button class="cw-chip ${filtro ? '' : 'on'}" data-action="panel-filter" data-service="${escapeHtml(svc)}" data-filter="">Todo</button>
            </div>
          </div>
        </div>
        <div class="cw-search" id="console-search-${escapeHtml(svc)}">
          <input type="search" placeholder="Buscar en esta consola…" aria-label="Buscar en la salida de ${escapeHtml(svc)}">
          <span class="cw-count" id="console-count-${escapeHtml(svc)}"></span>
          <button class="cw-nav" data-action="search-prev" data-service="${escapeHtml(svc)}" title="Coincidencia anterior">↑</button>
          <button class="cw-nav" data-action="search-next" data-service="${escapeHtml(svc)}" title="Coincidencia siguiente">↓</button>
          <button class="cw-nav" data-action="search-close" data-service="${escapeHtml(svc)}" title="Cerrar búsqueda">×</button>
        </div>
        <div class="console-body-wrapper" id="console-body-wrap-${escapeHtml(svc)}">
          <div class="console-viewport-body console-monitor-body" id="console-monitor-body-${escapeHtml(svc)}" style="font-size:${fontSize}px;"></div>
          <button class="console-jump-btn" id="console-jump-${escapeHtml(svc)}" data-action="resume-follow" data-service="${escapeHtml(svc)}" hidden title="Volver al final de la salida">Ir al final ↓</button>
        </div>
        <div class="console-panel-footer">
          <span class="cw-foot-name" title="${escapeHtml(svc)}">${escapeHtml(svc)}</span>
          <span class="cw-foot-chip" id="console-scrollpause-${escapeHtml(svc)}" data-action="resume-follow" data-service="${escapeHtml(svc)}" hidden title="Seguimiento en pausa: clic para volver al final">⏸ pausa por scroll</span>
          <span class="cw-foot-filter" id="console-filterlabel-${escapeHtml(svc)}">${escapeHtml(filtro)}</span>
          <div class="console-panel-footer-right">
            <span class="cw-foot-fresh" id="console-fresh-${escapeHtml(svc)}" hidden title="Tiempo transcurrido desde la última línea recibida">sin tráfico</span>
            <span class="console-footer-status" id="console-footer-status-${escapeHtml(svc)}">● LIVE</span>
            <span class="console-paused-pill" id="console-paused-${escapeHtml(svc)}" data-action="resume-follow" data-service="${escapeHtml(svc)}" style="display:none;" title="Seguimiento en pausa. Clic para volver al final.">PAUSADO</span>
            <span class="console-footer-runtime-tag" id="console-updated-${escapeHtml(svc)}">${escapeHtml(runtimeTagStr)}</span>
          </div>
        </div>
      `;

      const monitorBody = panel.querySelector('.console-monitor-body');
      if (monitorBody) {
        monitorBody.addEventListener('scroll', () => onPanelScroll(svc, monitorBody), { passive: true });
        /* La rueda desplaza el MURO, no la consola, salvo que la consola se haya
           activado con un clic (así el scroll del sitio no mueve las terminales). */
        monitorBody.addEventListener('wheel', (e) => {
          if (consoleWorkspace.wheelActive === svc) return;
          e.preventDefault();
          const contenedor = document.getElementById('consoleStageView') || document.getElementById('consoleMosaicGrid');
          if (contenedor) contenedor.scrollTop += e.deltaY;
        }, { passive: false });
        monitorBody.addEventListener('mousedown', () => activarRuedaConsola(svc));
      }

      function activarRuedaConsola(objetivo) {
        consoleWorkspace.wheelActive = objetivo;
        document.querySelectorAll('.console-panel').forEach((p) => {
          p.classList.toggle('is-wheel-active', p.dataset.service === objetivo);
        });
      }

      /* Reordenar por arrastre usando la cabecera como asa (sin tocar el cuerpo). */
      const head = panel.querySelector('.console-panel-header');
      if (head) {
        head.draggable = true;
        head.addEventListener('dragstart', (e) => {
          consoleWorkspace._dragging = svc;
          panel.classList.add('dragging');
          try { e.dataTransfer.setData('text/plain', svc); e.dataTransfer.effectAllowed = 'move'; } catch (_) {}
        });
        head.addEventListener('dragend', () => {
          consoleWorkspace._dragging = null;
          document.querySelectorAll('.console-panel').forEach((p) => p.classList.remove('dragging', 'drop-before', 'drop-after'));
        });
      }
      panel.addEventListener('dragover', (e) => {
        const desde = consoleWorkspace._dragging;
        if (!desde || desde === svc) return;
        e.preventDefault();
        const r = panel.getBoundingClientRect();
        const despues = (e.clientX - r.left) > r.width / 2;
        panel.classList.toggle('drop-after', despues);
        panel.classList.toggle('drop-before', !despues);
      });
      panel.addEventListener('dragleave', () => panel.classList.remove('drop-before', 'drop-after'));
      panel.addEventListener('drop', (e) => {
        e.preventDefault();
        const desde = consoleWorkspace._dragging;
        const r = panel.getBoundingClientRect();
        const despues = (e.clientX - r.left) > r.width / 2;
        panel.classList.remove('drop-before', 'drop-after');
        if (desde && desde !== svc) moverConsola(desde, svc, despues);
      });

      const searchBar = panel.querySelector('.cw-search');
      if (searchBar) {
        const input = searchBar.querySelector('input');
        input.addEventListener('input', () => {
          const q = input.value.trim();
          if (q) consoleWorkspace.queryMap.set(svc, q); else consoleWorkspace.queryMap.delete(svc);
          consoleWorkspace.matchIndexMap.set(svc, 0);
          renderPanelBody(svc, { force: true });
        });
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') { e.preventDefault(); panelSearchNav(svc, e.shiftKey ? -1 : 1); }
          if (e.key === 'Escape') {
            e.preventDefault();
            searchBar.classList.remove('open');
            consoleWorkspace.queryMap.delete(svc);
            renderPanelBody(svc, { force: true });
          }
        });
      }

      return panel;
    }

    function onPanelScroll(svc, monitorBody) {
      if (consoleWorkspace.controlMap.has(svc)) return;
      /* Un panel fuera de pantalla está deshidratado (cuerpo vacío): su scroll
         no lo mueve el usuario, así que no puede pausar el seguimiento. */
      const panelFresco = document.getElementById(`console-panel-${svc}`);
      if (panelFresco && panelFresco.dataset.hydrated !== '1') return;
      /* Los repintados mueven el scroll del panel (innerHTML + anclaje +
         scrollToBottom) y emiten eventos de scroll que NO son del usuario.  Si
         uno llegaba en un instante no-fondo, el seguimiento se desactivaba solo
         y aparecía "⏸ pausa por scroll" sin que nadie hubiera tocado nada. */
      if ((consoleWorkspace.scrollGuardUntil.get(svc) || 0) > performance.now()) return;
      const atBottom = ConsoleViewport.isAtBottom(monitorBody);
      const wasFollowing = consoleWorkspace.followMap.get(svc) !== false;
      const pausedPill = document.getElementById(`console-paused-${svc}`);
      const jumpBtn = document.getElementById(`console-jump-${svc}`);
      // Estado y pausa son mutuamente exclusivos en el pie del panel: mostrar
      // "● LIVE" junto a "PAUSADO" deja al usuario sin saber cuál es el estado
      // real.  Mientras el seguimiento está en pausa, sólo se ve la píldora.
      const statusEl = document.getElementById(`console-footer-status-${svc}`);
      const chip = document.getElementById(`console-scrollpause-${svc}`);

      if (atBottom && !wasFollowing) {
        consoleWorkspace.followMap.set(svc, true);
        if (pausedPill) pausedPill.style.display = 'none';
        if (statusEl) statusEl.style.display = '';
        if (jumpBtn) jumpBtn.hidden = true;
        if (chip) chip.hidden = true;
      } else if (!atBottom && wasFollowing) {
        consoleWorkspace.followMap.set(svc, false);
        if (pausedPill) pausedPill.style.display = 'inline-block';
        if (statusEl) statusEl.style.display = 'none';
        if (jumpBtn) jumpBtn.hidden = false;
        if (chip) chip.hidden = false;
      }
    }

    // -------------------------------------------------------------------------
    // Bounded, batched panel rendering (stream continues, DOM stays small)
    // -------------------------------------------------------------------------
    /**
     * Schedule work on the next animation frame, with a timer fallback.
     *
     * Measured in this Electron build: for a window the compositor is not
     * painting (audit harness, occluded or off-screen window)
     * `requestAnimationFrame` NEVER fires, while timers do.  Correctness must
     * therefore not depend on rAF — it is only a coalescing optimisation.
     */
    function scheduleFrame(callback) {
      let done = false;
      let respaldo = null;
      const run = () => {
        if (done) return;
        done = true;
        /* Cancelar el temporizador de respaldo al disparar el rAF: antes quedaba
           uno vivo por cada llamada (medido: 28 -> 53 al ciclar pestañas 5 veces). */
        if (respaldo !== null) {
          window.clearTimeout(respaldo);
          respaldo = null;
        }
        callback();
      };
      if (typeof window.requestAnimationFrame === 'function') {
        const rafId = window.requestAnimationFrame(run);
        respaldo = window.setTimeout(() => {
          if (done) return;
          if (typeof window.cancelAnimationFrame === 'function') {
            window.cancelAnimationFrame(rafId);
          }
          run();
        }, 100);
      } else {
        window.setTimeout(run, 50);
      }
    }

    function markPanelDirty(svc) {
      consoleWorkspace.dirtyPanels.add(svc);
      if (consoleWorkspace.renderScheduled) return;
      consoleWorkspace.renderScheduled = true;
      scheduleFrame(() => {
        consoleWorkspace.renderScheduled = false;
        const batch = Array.from(consoleWorkspace.dirtyPanels);
        consoleWorkspace.dirtyPanels.clear();
        const ahora = (typeof performance !== 'undefined' && performance.now)
          ? performance.now() : Date.now();
        batch.forEach((name) => {
          const desde = ahora - (consoleWorkspace.lastPaintMap.get(name) || 0);
          if (desde < WALL_PAINT_MS) {
            /* Aún no toca pintar: se reprograma para no perder la última línea. */
            if (!consoleWorkspace.paintTimers.has(name)) {
              const t = window.setTimeout(() => {
                consoleWorkspace.paintTimers.delete(name);
                markPanelDirty(name);
              }, Math.ceil(WALL_PAINT_MS - desde));
              consoleWorkspace.paintTimers.set(name, t);
            }
            return;
          }
          consoleWorkspace.lastPaintMap.set(name, ahora);
          renderPanelBody(name);
        });
      });
    }

    /** Sube la revisión de una consola: obliga a repintarla en el próximo pase. */
    function bumpPanelRevision(svc) {
      consoleWorkspace.revMap.set(svc, (consoleWorkspace.revMap.get(svc) || 0) + 1);
    }

    function renderPanelBody(svc, options = {}) {
      const body = document.getElementById(`console-monitor-body-${svc}`);
      if (!body) return;
      const panel = document.getElementById(`console-panel-${svc}`);
      const hydrated = panel && panel.dataset.hydrated === '1';
      if (!hydrated && !options.force) {
        /* Autocorrección: un panel puede quedar deshidratado (cuerpo vacío) y
           seguir a la vista —se veía en negro con el pie en «LIVE»—, y entonces
           ninguna línea nueva se pintaba.  Si está en pantalla se rehidrata aquí
           mismo en vez de esperar a que cambie la visibilidad. */
        if (panel && panelEstaEnPantalla(panel)) {
          hydratePanel(svc);
        } else {
          return;
        }
      }
      if (consoleWorkspace.controlMap.has(svc) && !options.force) return;

      /* La guarda va ANTES de calcular el render y vence incluso a los repintados
         forzados: el camino SSE repinta con {force:true}, así que limitarla a los
         no forzados no protegía nada (la selección se seguía perdiendo).  Sólo se
         protege si hay contenido: un cuerpo vacío debe poder pintarse. */
      const seleccionActiva = haySeleccionEn(body);
      if (seleccionActiva && body.querySelector('.console-line')) {
        if (!consoleWorkspace.paintTimers.has(svc)) {
          const t = window.setTimeout(() => {
            consoleWorkspace.paintTimers.delete(svc);
            markPanelDirty(svc);
          }, 500);
          consoleWorkspace.paintTimers.set(svc, t);
        }
        return;
      }

      /* Filtros y búsqueda POR CONSOLA (lenguaje del laboratorio). */
      const query = consoleWorkspace.queryMap.get(svc) || consoleWorkspace.outputSearchQuery || '';
      const filtro = consoleWorkspace.filterMap.get(svc) || consoleWorkspace.filterAll || '';
      const soloErrores = consoleWorkspace.errorsMap.get(svc) === true || consoleWorkspace.errorsAll === true;

      /* Guarda barata ANTES de construir el HTML: el sondeo cada 3 s marca
         "sucio" a todos los paneles aunque nada haya cambiado, y volver a
         construir 200 líneas por panel era trabajo tirado.  La revisión sólo
         sube cuando el contenido cambia de verdad (delta o last_line_ts nuevo). */
      const rev = consoleWorkspace.revMap.get(svc) || 0;
      const bufActual = consoleWorkspace.buffers.get(svc) || [];
      const enFocoPrev = consoleWorkspace.focusList.includes(svc) ? 1 : 0;
      const preKey = `${rev}|${bufActual.length}|${query}|${filtro}|${soloErrores}`
        + `|${consoleWorkspace.tailLines}|${consoleWorkspace.fontMap.get(svc) || 0}`
        + `|${consoleWorkspace.wallFontSize}|${enFocoPrev}`;
      if (panel && panel.dataset.preKey === preKey && !options.force) return;
      if (panel) panel.dataset.preKey = preKey;

      let lines = linesForPanel(svc);
      /* El final del búfer suele traer líneas en blanco (los servicios dejan
         separadores al escribir).  Con la salida anclada al fondo, la ventana
         visible quedaba llena de espacios y la consola se veía **negra** aunque
         el pie dijera LIVE (medido: 49 de 50 líneas vacías al final).  Se
         recortan SÓLO las del final; las interiores se conservan porque separan
         bloques del log. */
      let finConTexto = lines.length;
      while (finConTexto > 0 && !String(lines[finConTexto - 1]).trim()) finConTexto--;
      if (finConTexto < lines.length) lines = lines.slice(0, finConTexto);
      if (soloErrores) lines = lines.filter((l) => ConsoleViewport.classifyLine(l) === 'is-error');
      if (filtro) {
        const f = filtro.toLowerCase();
        lines = lines.filter((l) => l.toLowerCase().includes(f));
      }
      const rendered = ConsoleViewport.renderLines(lines, { query, filter: false });
      actualizarContadorBusqueda(svc, lines, query);
      /* La revisión entra en la clave: es lo único que distingue "llegaron líneas
         nuevas" de "el recorte tiene el mismo tamaño y termina en blanco". */
      const renderKey = `${rev}|${lines.length}|${lines.length ? lines[lines.length - 1] : ''}|${query}|${filtro}|${soloErrores}`;
      if (panel && panel.dataset.renderKey === renderKey && !options.force) return;
      if (panel) panel.dataset.renderKey = renderKey;

      /* Al maximizar (modo Enfoque) la letra crece para aprovechar el panel; si el
         usuario fijó un tamaño para esa consola, se respeta. */
      const enFoco = consoleWorkspace.focusList.includes(svc);
      const boost = (enFoco && !consoleWorkspace.fontMap.has(svc)) ? 2 : 0;
      const fontSize = (consoleWorkspace.fontMap.get(svc) || consoleWorkspace.wallFontSize) + boost;
      body.style.fontSize = fontSize + 'px';
      const fontLabel = document.getElementById(`console-font-${svc}`);
      if (fontLabel) fontLabel.textContent = fontSize + ' px';

      const following = consoleWorkspace.followMap.get(svc) !== false && consoleWorkspace.globalFollow;
      const previousTop = body.scrollTop;
      /* Ventana en la que los eventos de scroll del panel se atribuyen a este
         repintado y no al usuario (ver onPanelScroll). */
      consoleWorkspace.scrollGuardUntil.set(svc, performance.now() + 150);

      /* Selección de texto: reemplazar el innerHTML la destruye (se perdía o
         saltaba al bloque entero).  Si hay algo seleccionado EN ESTA consola no
         se repinta: se reintenta en medio segundo, cuando el usuario suelte. */
      body.innerHTML = rendered.count
        ? rendered.html
        : marcadorConsolaVacia(svc);

      anclarSalidaAbajo(svc, body);

      if (following && !haySeleccionEn(body)) {
        ConsoleViewport.scrollToBottom(body);
      } else {
        body.scrollTop = previousTop;
      }
    }

    /**
     * Ancla la salida al fondo del panel (como un tail real) sólo cuando sobra
     * espacio: así un panel grande no queda con un hueco vacío abajo, y cuando
     * la salida desborda el desplazamiento sigue funcionando normal.
     */
    function anclarSalidaAbajo(svc, body) {
      if (!body) return;
      const lineas = body.querySelectorAll('.console-line');
      body.style.paddingTop = '';
      if (!lineas.length) return;
      const cs = getComputedStyle(body);
      const interlineado = parseFloat(cs.lineHeight) || (parseFloat(cs.fontSize) * 1.4) || 16;
      const padSuperior = parseFloat(cs.paddingTop) || 0;
      const padInferior = parseFloat(cs.paddingBottom) || 0;
      const altoUtil = body.clientHeight - padSuperior - padInferior;
      const usado = lineas.length * interlineado;
      const relleno = Math.floor(altoUtil - usado);
      if (relleno > 4) body.style.paddingTop = relleno + 'px';
    }

    function hydratePanel(svc, options = {}) {
      const panel = document.getElementById(`console-panel-${svc}`);
      if (!panel) return;
      const wasHydrated = panel.dataset.hydrated === '1';
      panel.dataset.hydrated = '1';
      panel.classList.remove('is-offscreen');
      // Re-rendering an already hydrated panel costs ~10 ms of DOM work per
      // pass (measured), so only the first hydration is forced.
      if (!wasHydrated || options.force) {
        renderPanelBody(svc, { force: true });
      }
    }

    /**
     * Marcador de una consola sin líneas.
     *
     * Un servicio de desarrollo **no escribe si no recibe peticiones**, así que
     * un cuerpo vacío es normal y no debe parecer una consola rota: se explica el
     * estado real (en marcha/detenido), cuándo fue la última salida y qué hacer.
     */
    function marcadorConsolaVacia(svc) {
      /* Estado real del servicio (globalData), no el texto del pie: ese texto se
         actualiza después y dejaba el marcador desfasado («en marcha» en una
         consola detenida). */
      let enMarcha = false;
      try {
        const listas = [globalData.backend || [], globalData.frontend || []];
        let item = null;
        for (const lista of listas) { item = lista.find((x) => x.name === svc); if (item) break; }
        enMarcha = item ? !!item.online : /LIVE|ACTIVO|▶/i.test(
          (document.getElementById(`console-footer-status-${svc}`) || {}).textContent || '');
      } catch (_) { enMarcha = true; }
      const capturadas = (consoleWorkspace.buffers.get(svc) || []).length;
      let etiqueta = '';
      let estado = 'silent';
      try {
        const f = typeof panelFreshness === 'function' ? panelFreshness(svc) : null;
        if (f) { etiqueta = f.label || ''; estado = f.state || 'silent'; }
      } catch (_) { /* nunca debe romper el pintado */ }

      if (!enMarcha) {
        return `<div class="console-vacio is-parado">
            <div class="cv-titulo">⏹️ Detenido — sin salida capturada</div>
            <div class="cv-detalle">El servicio no está en marcha, así que no hay nada que mostrar.</div>
            <div class="cv-ayuda">Lánzalo con ▶ Iniciar (o «Iniciar en Dashboard») y su salida aparecerá aquí.</div>
          </div>`;
      }
      if (capturadas > 0 || (etiqueta && etiqueta !== 'sin tráfico')) {
        return `<div class="console-vacio is-marcha">
            <div class="cv-titulo">🟢 En marcha — sin salida nueva</div>
            <div class="cv-detalle">Última línea <b>${escapeHtml(etiqueta || 'hace un momento')}</b>; la captura sigue activa.</div>
            <div class="cv-ayuda">Un servicio de desarrollo no escribe si no recibe peticiones: la consola está al día y se llenará sola.</div>
          </div>`;
      }
      return `<div class="console-vacio is-marcha">
          <div class="cv-titulo">🟢 En marcha — todavía sin salida</div>
          <div class="cv-detalle">Arrancó y aún no ha escrito nada.</div>
          <div class="cv-ayuda">Si esperabas actividad, revisa 🩺 ¿Por qué no arranca? en la tarjeta del servicio.</div>
        </div>`;
    }

    /** ¿Hay texto seleccionado por el usuario dentro de este cuerpo? */
    function haySeleccionEn(body) {
      if (!body || typeof window.getSelection !== 'function') return false;
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.rangeCount) return false;
      const ancla = sel.anchorNode;
      if (!ancla) return false;
      const nodo = ancla.nodeType === 1 ? ancla : ancla.parentNode;
      return !!(nodo && body.contains(nodo));
    }

    /** ¿El panel está a la vista (o a un margen de estarlo)? */
    function panelEstaEnPantalla(panel) {
      const r = panel.getBoundingClientRect();
      if (!r.height) return false;
      return r.bottom > -PANEL_HYDRATE_MARGIN_PX && r.top < window.innerHeight + PANEL_HYDRATE_MARGIN_PX;
    }

    function dehydratePanel(panel, svc) {
      panel.dataset.hydrated = '0';
      panel.dataset.renderKey = '';
      panel.dataset.preKey = '';
      panel.classList.add('is-offscreen');
      const body = document.getElementById(`console-monitor-body-${svc}`);
      if (body) {
        /* Vaciar el cuerpo devuelve scrollTop a 0 y el navegador emite un evento
           de scroll que NO es del usuario: sin esta guarda la virtualización
           pausaba el seguimiento sola ("⏸ pausa por scroll" constante). */
        consoleWorkspace.scrollGuardUntil.set(svc, performance.now() + 300);
        body.innerHTML = '';
      }
    }

    /**
     * Card virtualisation.
     *
     * Measured in this Electron build (41.5 / Chromium on XWayland):
     * `IntersectionObserver` constructs but NEVER delivers a callback, neither
     * with the stage as root nor with the viewport as root (0 entries in 2.5 s),
     * so hydration must not depend on it.  Visibility is therefore computed
     * deterministically from element rectangles, throttled to one pass per
     * animation frame.  Offscreen consoles keep streaming into their ring
     * buffers; only their DOM is released (buffer != DOM).
     */
    const PANEL_HYDRATE_MARGIN_PX = 160;
    /*: Cuántas consolas se hidratan por frame (medido: 18 de golpe = ~345 ms de
       bloqueo; repartidas, la interfaz sigue respondiendo). */
    const HIDRATAR_POR_FRAME = 3;

    function syncPanelVisibility() {
      const root = document.getElementById('consoleStageView');
      if (!root) return;

      /* Con el muro en otra pestaña los rectángulos miden 0 y el retorno por
         altura cero dejaba 18 paneles hidratados que seguían reconstruyendo su
         DOM (medido: 696 → 1051 líneas con el muro oculto).  Si no está activo,
         se suelta todo el DOM y se sale. */
      if (!consoleWorkspace.isActiveTab || document.hidden) {
        document.querySelectorAll('.console-panel').forEach((panel) => {
          if (panel.dataset.hydrated === '1') dehydratePanel(panel, panel.dataset.service);
        });
        return;
      }

      const rootRect = root.getBoundingClientRect();
      const top = rootRect.top - PANEL_HYDRATE_MARGIN_PX;
      const bottom = rootRect.bottom + PANEL_HYDRATE_MARGIN_PX;

      /* Dos fases: primero TODAS las lecturas de layout y después todas las
         escrituras.  Intercalarlas forzaba un reflow por panel; una sola pasada
         llegó a costar 437 ms medidos. */
      const hidratar = [];
      const deshidratar = [];
      document.querySelectorAll('.console-panel').forEach((panel) => {
        const svc = panel.dataset.service;
        if (!svc) return;
        if (panel.classList.contains('is-focused')) return;
        if (panel.style.display === 'none') return;
        const r = panel.getBoundingClientRect();
        if (r.height <= 0) return;
        const onScreen = r.bottom > top && r.top < bottom;
        if (onScreen) {
          if (panel.dataset.hydrated !== '1') hidratar.push(svc);
        } else if (panel.dataset.hydrated === '1') {
          deshidratar.push([panel, svc]);
        }
      });
      /* Deshidratar es barato: se hace de una vez.  Hidratar construye el DOM
         de cada consola (puede costar cientos de ms en total), así que se
         reparte en trozos por frame para no bloquear el hilo principal. */
      deshidratar.forEach(([panel, svc]) => dehydratePanel(panel, svc));
      const lote = (pendientes) => {
        if (!pendientes.length) return;
        pendientes.splice(0, HIDRATAR_POR_FRAME).forEach((svc) => hydratePanel(svc));
        /* El alto en líneas enteras lo fija el CSS con `--cw-rows` (una sola
           vez), así que aquí no hay nada que recalcular por lote. */
        if (pendientes.length) scheduleFrame(() => lote(pendientes));
      };
      lote(hidratar);
    }

    function schedulePanelVisibilitySync() {
      if (consoleWorkspace.visibilityScheduled) return;
      consoleWorkspace.visibilityScheduled = true;
      scheduleFrame(() => {
        consoleWorkspace.visibilityScheduled = false;
        syncPanelVisibility();
      });
    }

    // -------------------------------------------------------------------------
    // Focus / fullscreen console (replaces the small floating modal)
    // -------------------------------------------------------------------------
    /**
     * Modo Enfoque 1/2/3 (equivalente al del laboratorio): las consolas marcadas
     * se mueven a una capa que ocupa todo el escenario, con plantillas y acople.
     */
    function applyFocusLayer() {
      const layer = document.getElementById('consoleFocusLayer');
      if (!layer) return;
      /* renderConsoleStage() vuelve a llamar aquí: sin esta guarda se produce
         recursión infinita (RangeError) al entrar o salir del Enfoque. */
      if (consoleWorkspace._applyingFocus) return;
      const lista = consoleWorkspace.focusList.filter((n) => consoleWorkspace.monitoredServices.has(n));

      if (!lista.length) {
        /* Devolver los paneles al muro ANTES de limpiar la capa: si se vacía el
           contenedor con los paneles dentro, se destruyen y queda la pantalla negra. */
        const salieron = [];
        document.querySelectorAll('.console-panel.is-focused').forEach((p) => {
          p.classList.remove('is-focused');
          p.style.order = '';
          salieron.push(p.dataset.service);
        });
        layer.hidden = true;
        consoleWorkspace.maximizedService = null;
        consoleWorkspace._applyingFocus = true;
        try { renderConsoleStage(); } finally { consoleWorkspace._applyingFocus = false; }
        /* Al salir del Enfoque la letra vuelve a su tamaño: hay que repintar,
           porque el render cacheado no cambia de clave al cambiar sólo el tamaño. */
        salieron.forEach((n) => renderPanelBody(n, { force: true }));
        const gridViejo = layer.querySelector('#cwFocusGrid');
        if (gridViejo) gridViejo.innerHTML = '';
        layer.innerHTML = '';
        paintFocusButton();
        return;
      }
      consoleWorkspace.maximizedService = lista.length === 1 ? lista[0] : null;

      let bar = layer.querySelector('.cw-focus-bar');
      let grid = layer.querySelector('#cwFocusGrid');
      if (!bar || !grid) {
        layer.innerHTML = '';
        bar = document.createElement('div');
        bar.className = 'cw-focus-bar';
        bar.innerHTML = `
          <b id="cwFocusCount" style="color:var(--accent)">${lista.length}</b>
          <span>consola${lista.length > 1 ? 's' : ''} en Enfoque · arrastra la cabecera de un panel sobre otro para reubicarlo</span>
          <span style="flex:1"></span>
          <label class="cw-field">Plantilla
            <select id="cwFocusLayout">
              <option value="auto">Automática</option>
              <option value="cols">En columnas</option>
              <option value="rows">En filas</option>
              <option value="big">1 grande + 2</option>
            </select>
          </label>
          <label class="cw-field" title="Añadir otra consola al Enfoque sin volver al muro">Añadir
            <select id="cwFocusAdd"></select>
          </label>
          <button class="cw-btn" id="cwFocusExit">⤡ Volver al muro</button>
        `;
        layer.appendChild(bar);
        grid = document.createElement('div');
        grid.className = 'cw-focus-grid';
        grid.id = 'cwFocusGrid';
        layer.appendChild(grid);

        bar.querySelector('#cwFocusLayout').addEventListener('change', (ev) => {
          consoleWorkspace.focusLayout = ev.target.value;
          saveConsoleWorkspaceStorage();
          applyFocusLayer();
        });
        bar.querySelector('#cwFocusAdd').addEventListener('change', (ev) => {
          const svc = ev.target.value;
          if (!svc) return;
          ev.target.value = '';
          if (consoleWorkspace.focusList.includes(svc)) return;
          if (consoleWorkspace.focusList.length >= 3) {
            showToast('⚠️ El Enfoque admite hasta 3 consolas.');
            return;
          }
          /* Sin esto, para poner 3 consolas en Enfoque había que salir al muro
             entre cada una: la capa ocupa toda la pantalla y tapa los paneles. */
          consoleWorkspace.focusList.push(svc);
          saveConsoleWorkspaceStorage();
          applyFocusLayer();
          showToast(`◎ ${svc} añadida al Enfoque`);
        });
        bar.querySelector('#cwFocusExit').addEventListener('click', () => {
          consoleWorkspace.focusList = [];
          consoleWorkspace.focusLayout = 'auto';
          saveConsoleWorkspaceStorage();
          applyFocusLayer();
          showToast('↩️ Volviste al muro completo');
        });
      }

      const layout = consoleWorkspace.focusLayout === 'auto'
        ? (lista.length === 3 ? 'big' : 'cols')
        : consoleWorkspace.focusLayout;

      const contador = bar.querySelector('#cwFocusCount');
      if (contador) contador.textContent = String(lista.length);
      const aviso = bar.querySelector('span');
      if (aviso) aviso.textContent = `${lista.length > 1 ? lista.length + ' consolas' : '1 consola'} en Enfoque · arrastra la cabecera de un panel sobre otro para reubicarlo`;
      const sel = bar.querySelector('#cwFocusLayout');
      if (sel && sel.value !== consoleWorkspace.focusLayout) sel.value = consoleWorkspace.focusLayout;

      const addSel = bar.querySelector('#cwFocusAdd');
      if (addSel) {
        const disponibles = Array.from(consoleWorkspace.monitoredServices)
          .filter((n) => !lista.includes(n))
          .sort();
        const firma = disponibles.join('|');
        if (addSel.dataset.firma !== firma) {
          addSel.innerHTML = '<option value="">— elegir —</option>'
            + disponibles.map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join('');
          addSel.dataset.firma = firma;
        }
        addSel.disabled = disponibles.length === 0;
      }

      grid.dataset.count = String(Math.min(lista.length, 3));
      grid.dataset.layout = layout;
      layer.hidden = false;

      /* Reubicar sólo con appendChild y `order`: nunca se destruye el panel. */
      lista.forEach((svc, i) => {
        const panel = document.getElementById(`console-panel-${svc}`);
        if (!panel) return;
        panel.classList.add('is-focused');
        panel.classList.remove('is-enfoque');
        panel.style.order = String(i);
        if (panel.parentElement !== grid) grid.appendChild(panel);
        hydratePanel(svc, { force: true });
      });
      Array.from(grid.querySelectorAll('.console-panel')).forEach((panel) => {
        if (lista.includes(panel.dataset.service)) return;
        panel.classList.remove('is-focused');
        panel.style.order = '';
      });
      paintFocusButton();
    }

    /** Muestra en la barra cuántas consolas están marcadas para Enfoque. */
    function paintFocusButton() {
      const btn = document.getElementById('btnWallFocus');
      if (!btn) return;
      const n = consoleWorkspace.focusList.length;
      btn.textContent = n ? `◎ Enfoque (${n})` : '◎ Enfoque';
      btn.classList.toggle('on', n > 0);
    }

    function toggleEnfoque(svc) {
      const i = consoleWorkspace.focusList.indexOf(svc);
      if (i >= 0) {
        consoleWorkspace.focusList.splice(i, 1);
        saveConsoleWorkspaceStorage();
        paintFocusButton();
        applyFocusLayer();
        if (!consoleWorkspace.focusList.length) renderConsoleStage();
        showToast(`◎ ${svc} fuera del Enfoque`);
        return;
      }
      if (consoleWorkspace.focusList.length >= 3) {
        showToast('◎ El modo Enfoque admite hasta 3 consolas');
        return;
      }
      consoleWorkspace.focusList.push(svc);
      saveConsoleWorkspaceStorage();
      paintFocusButton();
      refreshPanelControls(svc);
      showToast(`◎ ${svc} marcada · pulsa «Enfoque» en la barra para verla en grande`);
    }

    // -------------------------------------------------------------------------
    // Stage rendering
    // -------------------------------------------------------------------------
    function renderConsoleTabsStrip(monitored) {
      const tabsStrip = document.getElementById('consoleTabsStrip');
      if (!tabsStrip) return;
      tabsStrip.innerHTML = '';
      monitored.forEach(svc => {
        const isActive = (svc === consoleWorkspace.activeTab);
        const isControl = consoleWorkspace.controlMap.has(svc);
        const tabItem = document.createElement('div');
        tabItem.className = `console-tab-item ${isActive ? 'active' : ''}`;
        tabItem.dataset.action = 'select-tab';
        tabItem.dataset.service = svc;
        tabItem.innerHTML = `
          <span>${isControl ? '🎮' : '👁'}</span>
          <span>${escapeHtml(svc)}</span>
          <span class="console-tab-close" data-action="close-panel" data-service="${escapeHtml(svc)}" title="Cerrar panel">✕</span>
        `;
        tabsStrip.appendChild(tabItem);
      });
    }

    function placePanel(panel, container) {
      if (panel.classList.contains('is-focused')) return;
      if (panel.parentElement !== container) container.appendChild(panel);
    }

    /**
     * ¿El servicio está detenido y además sin salida acumulada?
     *
     * Sólo esos paneles son puro hueco en el mosaico: no hay nada que leer ni
     * nada en curso.  Un servicio detenido que conserva su última salida sí
     * merece su celda, porque esa salida es la que explica por qué se cayó.
     */
    function isIdleConsoleService(svcName, svc) {
      if (getServiceStatusState(svc) !== 'stopped') return false;
      const buf = consoleWorkspace.buffers.get(svcName);
      return !buf || buf.length === 0;
    }

    /**
     * Franja compacta con los servicios detenidos y sin salida.
     *
     * Sustituye a las celdas vacías del mosaico.  Cada ficha reutiliza la acción
     * `quick-start` que ya maneja la delegación de eventos de `#tab-consoles`,
     * así que no introduce ninguna ruta de ejecución nueva.
     */
    function renderIdleConsoleStrip(svcNames) {
      const stage = document.getElementById('consoleStageView');
      if (!stage) return;

      let strip = document.getElementById('consoleIdleStrip');
      if (!strip) {
        strip = document.createElement('div');
        strip.id = 'consoleIdleStrip';
        strip.className = 'console-idle-strip';
        stage.appendChild(strip);
      }

      if (!svcNames || !svcNames.length) {
        strip.classList.remove('is-visible');
        strip.innerHTML = '';
        return;
      }

      const byName = new Map(getAllServicesList().map(s => [s.name, s]));
      const ordered = svcNames.slice().sort();

      strip.innerHTML = `
        <span class="console-idle-strip-label">Detenidos sin salida (${ordered.length})</span>
        ${ordered.map(name => {
          const svc = byName.get(name) || {};
          const port = svc.port ? ` :${escapeHtml(svc.port)}` : '';
          return `<button type="button" class="console-idle-chip" data-action="quick-start" data-service="${escapeHtml(name)}" data-port="${escapeHtml(svc.port || 0)}" title="Iniciar ${escapeHtml(name)}">▶ ${escapeHtml(name)}${port}</button>`;
        }).join('')}
      `;
      strip.classList.add('is-visible');
    }

    function renderConsoleStage() {
      const emptyState = document.getElementById('consoleEmptyState');
      const mosaicGrid = document.getElementById('consoleMosaicGrid');
      const groupedView = document.getElementById('consoleGroupedView');
      const tabsStrip = document.getElementById('consoleTabsStrip');
      const sessionCountElem = document.getElementById('consoleSessionCount');
      const footerDotsElem = document.getElementById('consoleFooterDots');
      const footerModeElem = document.getElementById('consoleFooterMode');
      const stageView = document.getElementById('consoleStageView');
      const workspace = document.getElementById('consoleWorkspace');

      if (!mosaicGrid || !emptyState || !tabsStrip || !stageView) return;

      // Density tokens live on the scroll container so cards inherit them.
      stageView.className = `console-stage-view density-${consoleWorkspace.density}`;
      if (workspace) workspace.classList.toggle('is-sidebar-collapsed', consoleWorkspace.sidebarCollapsed);

      const monitored = Array.from(consoleWorkspace.monitoredServices);

      if (monitored.length > 0) {
        if (!consoleWorkspace.activeTab || !consoleWorkspace.monitoredServices.has(consoleWorkspace.activeTab)) {
          consoleWorkspace.activeTab = monitored[0];
        }
      } else {
        consoleWorkspace.activeTab = null;
        consoleWorkspace.maximizedService = null;
      }

      // Toolbar state sync
      document.querySelectorAll('#consoleViewModeGroup button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === consoleWorkspace.viewMode);
      });
      document.querySelectorAll('#consoleGroupModeGroup button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.group === consoleWorkspace.groupMode);
      });
      const gridSelect = document.getElementById('consoleGridSelect');
      if (gridSelect && gridSelect.value !== consoleWorkspace.gridCols) {
        gridSelect.value = consoleWorkspace.gridCols;
      }
      if (mosaicGrid && consoleWorkspace.gridCols && consoleWorkspace.gridCols !== 'auto') {
        mosaicGrid.dataset.cols = consoleWorkspace.gridCols;
      }
      const densitySelect = document.getElementById('consoleDensitySelect');
      if (densitySelect && densitySelect.value !== consoleWorkspace.density) {
        densitySelect.value = consoleWorkspace.density;
      }
      const wallFontLabel = document.getElementById('consoleWallFont');
      if (wallFontLabel) wallFontLabel.textContent = consoleWorkspace.wallFontSize + ' px';

      if (monitored.length === 0) {
        emptyState.style.display = 'flex';
        mosaicGrid.style.display = 'none';
        if (groupedView) groupedView.style.display = 'none';
        tabsStrip.hidden = true;
        if (sessionCountElem) sessionCountElem.innerText = '0 sesiones';
        if (footerDotsElem) footerDotsElem.innerText = '● 0 consolas abiertas';
        if (footerModeElem) footerModeElem.innerText = '';
        applyFocusLayer();
        updateRailCounters();
        return;
      }

      emptyState.style.display = 'none';
      const controlCount = consoleWorkspace.controlMap.size;
      const monitorCount = monitored.length - controlCount;

      if (sessionCountElem) sessionCountElem.innerText = `${monitored.length} sesiones`;
      if (footerDotsElem) {
        footerDotsElem.innerText = `● ${monitored.length} consolas · ${monitorCount} lectura · ${controlCount} control`;
      }
      if (footerModeElem) {
        footerModeElem.innerText = (consoleWorkspace.viewMode === 'tabs'
          ? 'Modo pestañas — el resto de consolas sigue recibiendo salida'
          : 'Mosaico — la rueda desplaza la rejilla; sobre una consola, su historial')
          + ' · «hace Nm» en el pie = sin líneas nuevas; la consola sigue en vivo';
      }

      // Reconcile: remove panels that are no longer monitored
      document.querySelectorAll('.console-panel').forEach(panel => {
        const svc = panel.dataset.service;
        if (!consoleWorkspace.monitoredServices.has(svc)) {
          if (consoleWorkspace.controlMap.has(svc)) stopControlMode(svc);
          panel.remove();
        }
      });

      const ensurePanel = (svc) => {
        let panel = document.getElementById(`console-panel-${svc}`);
        if (!panel) {
          panel = createConsolePanelElement(svc);
        }
        return panel;
      };

      if (consoleWorkspace.viewMode === 'tabs') {
        tabsStrip.hidden = false;
        renderConsoleTabsStrip(monitored);
        mosaicGrid.className = 'console-mosaic-grid grid-1';
        mosaicGrid.style.display = 'grid';
        if (groupedView) groupedView.style.display = 'none';

        monitored.forEach(svc => {
          const panel = ensurePanel(svc);
          panel.style.display = (svc === consoleWorkspace.activeTab) ? 'flex' : 'none';
          placePanel(panel, mosaicGrid);
        });
        // Only the focused tab hydrates; the rest keep buffering offscreen.
        hydratePanel(consoleWorkspace.activeTab, { force: true });
        renderIdleConsoleStrip([]);

      } else if (consoleWorkspace.groupMode === 'grouped' && groupedView) {
        tabsStrip.hidden = true;
        mosaicGrid.style.display = 'none';
        groupedView.style.display = 'flex';
        renderGroupedConsoleStage(monitored);
        renderIdleConsoleStrip([]);

      } else {
        tabsStrip.hidden = true;
        if (groupedView) groupedView.style.display = 'none';
        mosaicGrid.className = `console-mosaic-grid grid-${consoleWorkspace.gridCols}`;
        mosaicGrid.dataset.cols = String(consoleWorkspace.gridCols);
        mosaicGrid.style.display = 'grid';

        // 1:1 con el laboratorio: todas las consolas monitorizadas ocupan su celda,
        // en el orden elegido (manual por arrastre, o por nombre/puerto/tipo).
        const filtroNombre = consoleWorkspace.nameFilter || '';
        const porNombre = filtroNombre
          ? monitored.filter((n) => {
              if (n.toLowerCase().includes(filtroNombre)) return true;
              const p = String(getPanelPort(n) || '');
              return p.includes(filtroNombre);
            })
          : monitored;
        /* "Solo activas": oculta las consolas sin sesión viva.  Al arrancar un
           servicio, el broker lo marca RUNNING y su tarjeta entra sola. */
        const visibles = consoleWorkspace.onlyActive
          ? porNombre.filter((n) => esServicioActivo(n))
          : porNombre;
        const conjunto = new Set(visibles);
        monitored.forEach((svc) => {
          if (conjunto.has(svc)) return;
          const panel = document.getElementById(`console-panel-${svc}`);
          if (panel) panel.style.display = 'none';
        });
        wallOrder(visibles).forEach((svc, i) => {
          const panel = ensurePanel(svc);
          panel.style.display = 'flex';
          /* `order` reordena la rejilla sin mover nodos en el DOM (mover un panel
             con xterm dentro rompería su lienzo). */
          panel.style.order = String(i);
          placePanel(panel, mosaicGrid);
        });
        if (footerDotsElem && consoleWorkspace.onlyActive) {
          footerDotsElem.innerText = `● ${visibles.length} de ${monitored.length} consolas activas`;
        }
        renderIdleConsoleStrip([]);
      }

      applyFocusLayer();
      updateRailCounters();
      schedulePanelVisibilitySync();
    }

    function renderGroupedConsoleStage(monitored) {
      const groupedView = document.getElementById('consoleGroupedView');
      if (!groupedView) return;

      const groups = [
        { key: 'backend', title: 'Backends (Django)', svcs: [] },
        { key: 'frontend', title: 'Frontends (Webpack)', svcs: [] },
        { key: 'worker', title: 'Workers (Celery)', svcs: [] },
        { key: 'consumer', title: 'Consumers (RabbitMQ)', svcs: [] },
        { key: 'beat', title: 'Schedulers (Celery Beat)', svcs: [] },
        { key: 'auxiliary', title: 'Auxiliares y Servicios', svcs: [] },
      ];

      monitored.forEach(svc => {
        const cat = getServiceCategory({ name: svc });
        const g = groups.find(grp => grp.key === cat) || groups[groups.length - 1];
        g.svcs.push(svc);
      });

      const activeGroups = groups.filter(g => g.svcs.length > 0);
      groupedView.innerHTML = '';

      activeGroups.forEach(grp => {
        const isCollapsed = consoleWorkspace.collapsedGroups.has(grp.key);
        const section = document.createElement('div');
        section.className = `console-group-section ${isCollapsed ? 'is-collapsed' : ''}`;
        section.dataset.groupKey = grp.key;

        section.innerHTML = `
          <div class="console-group-header" data-action="toggle-group-collapse" data-group="${grp.key}">
            <div class="console-group-title">
              <span>${grp.key === 'backend' ? '🐍' : (grp.key === 'frontend' ? '⚛️' : (grp.key === 'worker' ? '⚙️' : (grp.key === 'consumer' ? '🐰' : '🧩')))}</span>
              <span>${grp.title}</span>
              <span class="console-group-badge">${grp.svcs.length}</span>
            </div>
            <span class="console-group-chevron">▼</span>
          </div>
          <div class="console-group-grid grid-${consoleWorkspace.gridCols}"></div>
        `;

        const gridContainer = section.querySelector('.console-group-grid');
        grp.svcs.forEach(svc => {
          let panel = document.getElementById(`console-panel-${svc}`);
          if (!panel) {
            panel = createConsolePanelElement(svc);
          }
          panel.style.display = 'flex';
          placePanel(panel, gridContainer);
        });

        groupedView.appendChild(section);
      });
    }

    async function toggleMonitoredService(svc) {
      if (consoleWorkspace.monitoredServices.has(svc)) {
        if (consoleWorkspace.controlMap.has(svc)) {
          await stopControlMode(svc);
        }
        if (consoleWorkspace.maximizedService === svc) consoleWorkspace.maximizedService = null;
        consoleWorkspace.monitoredServices.delete(svc);
      } else {
        consoleWorkspace.monitoredServices.add(svc);
        consoleWorkspace.followMap.set(svc, true);
      }
      saveConsoleWorkspaceStorage();
      renderConsoleSidebarServices();
      renderConsoleStage();
    }

    // -------------------------------------------------------------------------
    // Monitor <-> Control mode
    // -------------------------------------------------------------------------
    async function startControlMode(svc) {
      if (!window.devconsoleTerminal) {
        showToast('ℹ️ Terminal interactiva activa en Electron Desktop. Abriendo visor Tilix externo...');
        await openTilixViewer(svc);
        return;
      }

      if (consoleWorkspace.controlMap.has(svc)) {
        return;
      }

      if (consoleWorkspace.controlMap.size >= 4) {
        showToast('⚠️ Límite de seguridad alcanzado: máximo 4 terminales interactivas simultáneas.');
        return;
      }

      const bodyWrap = document.getElementById(`console-body-wrap-${svc}`);
      updateControlButton(svc, true);
      const btnCtrl = document.getElementById(`console-btn-ctrl-${svc}`);
      const pausedPill = document.getElementById(`console-paused-${svc}`);
      const jumpBtn = document.getElementById(`console-jump-${svc}`);
      const footerStatus = document.getElementById(`console-footer-status-${svc}`);
      const panel = document.getElementById(`console-panel-${svc}`);
      if (!bodyWrap) return;

      if (pausedPill) pausedPill.style.display = 'none';
      if (jumpBtn) jumpBtn.hidden = true;
      if (footerStatus) {
        footerStatus.className = 'console-footer-status is-control';
        footerStatus.innerText = '● CONTROL';
      }
      if (panel) panel.classList.add('is-control-mode');

      // Hide monitor viewport
      const monitorBody = document.getElementById(`console-monitor-body-${svc}`);
      if (monitorBody) monitorBody.style.display = 'none';

      const banner = document.createElement('div');
      banner.className = 'console-banner banner-control';
      banner.id = `console-banner-${svc}`;
      banner.innerHTML = `<span>⚠️ MODO CONTROL ACTIVO: conectado a tmux. Las teclas y Ctrl+C afectan al proceso real.</span>`;

      const controlBody = document.createElement('div');
      controlBody.className = 'console-control-body';
      controlBody.id = `console-control-body-${svc}`;

      bodyWrap.appendChild(banner);
      bodyWrap.appendChild(controlBody);

      try {
        await cargarXterm();
        if (typeof Terminal === 'undefined') {
          throw new Error('Librería xterm.js no disponible.');
        }

        const term = new Terminal({
          cursorBlink: true,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: 12,
          theme: {
            /* Paleta del tema activo (theme.js / themes.css) */
            ...(window.SisperTheme ? SisperTheme.termTheme() : {
            background: '#020409',
            foreground: '#e2e8f0',
            cursor: '#38bdf8',
            selectionBackground: 'rgba(56, 189, 248, 0.3)',
            black: '#020409',
            red: '#ef4444',
            green: '#22c55e',
            yellow: '#eab308',
            blue: '#3b82f6',
            magenta: '#a855f7',
            cyan: '#06b6d4',
            white: '#f8fafc',
            brightBlack: '#475569',
            brightRed: '#f87171',
            brightGreen: '#4ade80',
            brightYellow: '#fde047',
            brightBlue: '#60a5fa',
            brightMagenta: '#c084fc',
            brightCyan: '#22d3ee',
            brightWhite: '#ffffff',
            })
          },
        });

        term.open(controlBody);

        const cols = Math.max(40, Math.floor((controlBody.clientWidth - 16) / 8)) || 80;
        const rows = Math.max(10, Math.floor((controlBody.clientHeight - 16) / 16)) || 24;

        const initResult = await window.devconsoleTerminal.init({
          service: svc,
          cols,
          rows,
        });

        const termId = initResult.id;

        const dataDisposable = term.onData((data) => {
          window.devconsoleTerminal.sendData(termId, data);
        });

        const unsubOutput = window.devconsoleTerminal.onOutput((id, data) => {
          if (id === termId) {
            term.write(data);
          }
        });

        const unsubExit = window.devconsoleTerminal.onExit((id, code, sig) => {
          if (id === termId) {
            term.write(`\r\n\x1b[33m[Sesión finalizada (código: ${code ?? 0}, señal: ${sig ?? 'ninguna'})]\x1b[0m\r\n`);
          }
        });

        let resizeTimer = null;
        const resizeObserver = new ResizeObserver((entries) => {
          if (!entries.length) return;
          clearTimeout(resizeTimer);
          resizeTimer = setTimeout(() => {
            if (!term || !term.element) return;
            const newCols = Math.max(40, Math.floor((controlBody.clientWidth - 16) / 8));
            const newRows = Math.max(10, Math.floor((controlBody.clientHeight - 16) / 16));
            try {
              term.resize(newCols, newRows);
              window.devconsoleTerminal.resize(termId, newCols, newRows);
            } catch (_) { /* xterm already disposed */ }
          }, 100);
        });
        resizeObserver.observe(controlBody);

        consoleWorkspace.controlMap.set(svc, {
          id: termId,
          term,
          dataDisposable,
          unsubOutput,
          unsubExit,
          resizeObserver,
        });

        if (btnCtrl) {
          btnCtrl.className = 'console-tool-btn btn-monitor';
          btnCtrl.dataset.action = 'exit-control';
          btnCtrl.innerText = '👁';
          btnCtrl.title = 'Liberar la terminal interactiva y volver a modo lectura';
        }

        renderConsoleSidebarServices();
        renderConsoleStage();
        term.focus();

        showToast(`🎮 Control interactivo activado para ${svc}. Precaución con Ctrl+C.`);

      } catch (err) {
        console.error('[console-workspace] Error iniciando control:', err);
        showToast(`❌ Error iniciando control en ${svc}: ${err.message}`);
        if (banner) banner.remove();
        if (controlBody) controlBody.remove();
        if (monitorBody) monitorBody.style.display = 'block';
        if (panel) panel.classList.remove('is-control-mode');
      }
    }

    async function stopControlMode(svc) {
      const entry = consoleWorkspace.controlMap.get(svc);
      if (!entry) return;

      const { id, term, dataDisposable, unsubOutput, unsubExit, resizeObserver } = entry;
      try {
        if (resizeObserver) resizeObserver.disconnect();
        if (dataDisposable && typeof dataDisposable.dispose === 'function') dataDisposable.dispose();
        if (typeof unsubOutput === 'function') unsubOutput();
        if (typeof unsubExit === 'function') unsubExit();
        if (window.devconsoleTerminal && id) {
          await window.devconsoleTerminal.destroy(id);
        }
        if (term && typeof term.dispose === 'function') {
          term.dispose();
        }
      } catch (err) {
        console.warn(`[console-workspace] Error deteniendo control de ${svc}:`, err);
      }

      consoleWorkspace.controlMap.delete(svc);

      const banner = document.getElementById(`console-banner-${svc}`);
      if (banner) banner.remove();

      const controlBody = document.getElementById(`console-control-body-${svc}`);
      if (controlBody) controlBody.remove();

      const monitorBody = document.getElementById(`console-monitor-body-${svc}`);
      if (monitorBody) monitorBody.style.display = 'block';

      const panel = document.getElementById(`console-panel-${svc}`);
      if (panel) panel.classList.remove('is-control-mode');

      const footerStatus = document.getElementById(`console-footer-status-${svc}`);
      if (footerStatus) {
        footerStatus.className = 'console-footer-status';
        footerStatus.innerText = '● LIVE';
      }

      updateControlButton(svc, false);

      renderConsoleSidebarServices();
      renderConsoleStage();
      showToast(`👁️ Modo monitor restaurado para ${svc}. El servicio sigue corriendo en tmux.`);
    }

    // -------------------------------------------------------------------------
    // Live data ingestion
    // -------------------------------------------------------------------------
    function stampPanelUpdate(svc) {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      const ss = String(now.getSeconds()).padStart(2, '0');
      consoleWorkspace.lastUpdateMap.set(svc, `${hh}:${mm}:${ss}`);
      const elem = document.getElementById(`console-updated-${svc}`);
      if (elem) elem.innerText = `${hh}:${mm}:${ss}`;
      const filtroLbl = document.getElementById(`console-filterlabel-${svc}`);
      if (filtroLbl) filtroLbl.textContent = consoleWorkspace.filterMap.get(svc) || (consoleWorkspace.errorsMap.get(svc) === true ? 'solo errores' : '');
    }

    // -------------------------------------------------------------------------
    // Frescura de tráfico (Fase 4): "hace 15s" / "hace 2m" / "sin tráfico"
    // -------------------------------------------------------------------------
    /**
     * Guarda el desfase entre el reloj del navegador y el del servidor.
     *
     * SÓLO se le puede pasar un instante que signifique "ahora" en el servidor
     * (`timestamp` de instantánea, de sondeo o de un delta).  Pasarle un
     * `last_line_ts` —que puede ser de hace 23 minutos— desplazaba el desfase
     * hacia atrás y todas las consolas parpadeaban entre "hace 0s" y su edad
     * real en cada sondeo.
     */
    function noteServerClock(tsSec) {
      if (!tsSec || typeof tsSec !== 'number' || !isFinite(tsSec)) return;
      consoleWorkspace.serverClockOffsetMs = (tsSec * 1000) - Date.now();
    }

    /** Registra que este servicio acaba de recibir salida nueva. */
    function touchPanelTraffic(svc, tsSec) {
      if (!svc) return;
      const at = (typeof tsSec === 'number' && isFinite(tsSec) && tsSec > 0)
        ? tsSec
        : (Date.now() + consoleWorkspace.serverClockOffsetMs) / 1000;
      const previo = consoleWorkspace.lastLineTsMap.get(svc) || 0;
      if (at > previo) consoleWorkspace.lastLineTsMap.set(svc, at);
      refreshPanelFreshness(svc);
    }

    /** Segundos transcurridos desde la última línea recibida (null si nunca hubo). */
    function panelIdleSeconds(svc) {
      const ts = consoleWorkspace.lastLineTsMap.get(svc);
      if (!ts) return null;
      const ahora = (Date.now() + consoleWorkspace.serverClockOffsetMs) / 1000;
      return Math.max(0, Math.floor(ahora - ts));
    }

    /** Etiqueta y severidad de la frescura de una consola. */
    function panelFreshness(svc) {
      const s = panelIdleSeconds(svc);
      if (s === null) return { label: 'sin tráfico', state: 'silent' };
      let label;
      if (s < 60) label = `hace ${s}s`;
      else if (s < 3600) label = `hace ${Math.floor(s / 60)}m`;
      else if (s < 86400) label = `hace ${Math.floor(s / 3600)}h`;
      else label = `hace ${Math.floor(s / 86400)}d`;
      const state = s < 60 ? 'fresh' : (s < 300 ? 'idle' : 'stale');
      return { label, state };
    }

    /** Pinta el indicador de frescura de una consola concreta. */
    function refreshPanelFreshness(svc) {
      const el = document.getElementById(`console-fresh-${svc}`);
      if (!el) return;
      if (consoleWorkspace.controlMap.has(svc)) { el.hidden = true; return; }
      el.hidden = false;
      const { label, state } = panelFreshness(svc);
      el.classList.toggle('is-fresh', state === 'fresh');
      el.classList.toggle('is-idle', state === 'idle');
      el.classList.toggle('is-stale', state === 'stale');
      el.classList.toggle('is-silent', state === 'silent');
      if (el.textContent !== label) el.textContent = label;
      /* El tooltip explica que "hace 9m" NO significa consola pegada: dice
         cuántas líneas lleva capturadas.  Un servicio de desarrollo no escribe
         si no recibe peticiones, y sin este dato el indicador asusta. */
      const capturadas = (consoleWorkspace.buffers.get(svc) || []).length;
      const detalle = state === 'silent'
        ? 'Sin líneas capturadas todavía (el servicio no ha escrito nada).'
        : `${capturadas} línea(s) capturadas. Última ${label}. La consola está al día:`
          + ' un servicio de desarrollo no escribe si no recibe peticiones.';
      if (el.title !== detalle) el.title = detalle;
    }

    /** Refresca los indicadores del muro (lo llama el reloj, 1 vez por segundo). */
    function refreshWallFreshness() {
      document.querySelectorAll('.console-panel').forEach((panel) => {
        const svc = panel.dataset.service;
        if (svc) refreshPanelFreshness(svc);
      });
    }

    function updatePanelStatusVisuals(svc, status, isStandby) {
      /* Si la consola sólo muestra su marcador de estado, se rehace con el
         estado nuevo (arrancó/detuvo) sin esperar a que llegue una línea. */
      try {
        const b = document.getElementById(`console-monitor-body-${svc}`);
        if (b && !b.querySelector('.console-line') && b.querySelector('.console-vacio')) {
          renderPanelBody(svc, { force: true });
        }
      } catch (_) { /* el pintado nunca debe romper la actualización de estado */ }

      const state = getServiceStatusState({ status, is_standby: isStandby });
      const label = CONSOLE_STATUS_LABEL[state] || 'Detenido';

      const dot = document.getElementById(`console-status-dot-${svc}`);
      if (dot) {
        dot.className = `console-panel-dot ${state}`;
        dot.title = label;
      }
      const footerStatus = document.getElementById(`console-footer-status-${svc}`);
      if (footerStatus && !consoleWorkspace.controlMap.has(svc)) {
        footerStatus.className = `console-footer-status ${state === 'running' ? '' : 'is-stopped'}`;
        footerStatus.innerText = state === 'running' ? '● LIVE' : `● ${label.toUpperCase()}`;
      }
      // Mantiene al día la etiqueta de estado y los botones Iniciar/Parar del menú.
      if (!consoleWorkspace.controlMap.has(svc)) refreshPanelControls(svc);
    }

    /**
     * ¿Tiene este servicio una consola viva?  Lo usa el filtro "Solo activas":
     * el catálogo base son 32 servicios y la mayoría están detenidos casi todo
     * el tiempo.  Un servicio recién arrancado entra solo en cuanto el broker lo
     * ve como RUNNING.
     */
    function esServicioActivo(nombre) {
      const item = consoleWorkspace.catalogMap.get(nombre);
      if (item && item.status) return item.status !== 'STOPPED';
      const base = (globalData.backend || []).concat(globalData.frontend || []);
      const g = base.find((s) => s.name === nombre);
      return !!(g && g.online);
    }

    function updateMonitorPanelContent(item) {
      if (consoleWorkspace.paused) return;   // muro en pausa: se conserva lo visible
      if (consoleWorkspace.controlMap.has(item.name)) return;

      const lines = item.recent_lines || item.lines || [];
      const tsPrevio = consoleWorkspace.lastLineTsMap.get(item.name) || 0;
      if (lines.length > 0) {
        consoleWorkspace.buffers.set(item.name, lines.slice(-1000));
      }
      /* El sondeo trae la marca de la última línea real: es lo que permite
         distinguir "en reposo hace 20m" de "sin tráfico" al recargar. */
      if (item.last_line_ts) touchPanelTraffic(item.name, item.last_line_ts);
      /* Si el backend trae una última línea más nueva, el contenido cambió. */
      if ((item.last_line_ts || 0) > tsPrevio) bumpPanelRevision(item.name);
      updatePanelStatusVisuals(item.name, item.status, item.is_standby);
      markPanelDirty(item.name);
    }

    function handleLiveDeltas(deltas) {
      if (!Array.isArray(deltas)) return;

      deltas.forEach(delta => {
        const svc = delta.service;
        const newLines = delta.lines || [];
        const isReset = Boolean(delta.reset);
        /* `delta.timestamp` es el instante de emisión en el servidor: sí vale
           como referencia de reloj (a diferencia de `last_line_ts`). */
        if (delta.timestamp) noteServerClock(delta.timestamp);

        let curBuffer = consoleWorkspace.buffers.get(svc) || [];
        if (isReset) {
          curBuffer = newLines.slice(-1000);
        } else if (newLines.length > 0) {
          curBuffer = curBuffer.concat(newLines).slice(-1000);
        }
        consoleWorkspace.buffers.set(svc, curBuffer);
        if (isReset || newLines.length > 0) bumpPanelRevision(svc);

        if (delta.status) {
          const catItem = consoleWorkspace.catalogMap.get(svc) || { name: svc };
          catItem.status = delta.status;
          consoleWorkspace.catalogMap.set(svc, catItem);
          updatePanelStatusVisuals(svc, delta.status, catItem.is_standby);
        }

        if (!consoleWorkspace.monitoredServices.has(svc)) return;

        if (newLines.length > 0) {
          stampPanelUpdate(svc);
          touchPanelTraffic(svc, delta.last_line_ts || delta.timestamp);
          markPanelDirty(svc);
        }
      });
    }

    function connectLiveConsoleStream() {
      consoleWorkspace.sseHealthy = false;   // hasta que onopen confirme
      if (consoleWorkspace.eventSource) {
        try { consoleWorkspace.eventSource.close(); } catch (_) { /* already closed */ }
        consoleWorkspace.eventSource = null;
      }

      const liveBadge = document.getElementById('consoleLiveIndicator');

      try {
        const es = new EventSource('/api/services/stream');
        consoleWorkspace.eventSource = es;

        es.onopen = () => {
          consoleWorkspace.sseHealthy = true;
          if (liveBadge) {
            liveBadge.className = 'console-live-badge';
            liveBadge.innerHTML = '<span class="dot"></span> En vivo';
          }
        };

        es.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'snapshot' && msg.data) {
              const snapshot = msg.data;
              noteServerClock(snapshot.timestamp);
              if (Array.isArray(snapshot.services)) {
                consoleWorkspace.brokerNames = new Set(snapshot.services.map((s) => s.name));
                snapshot.services.forEach(item => {
                  consoleWorkspace.catalogMap.set(item.name, item);
                  if (item.lines) {
                    consoleWorkspace.buffers.set(item.name, item.lines.slice(-1000));
                  }
                  updateMonitorPanelContent(item);
                });
                /* Una auxiliar recién lanzada debe tener tarjeta ya. */
                entrandoAlMuro();
              }
              renderConsoleSidebarServices();
            } else if (msg.type === 'delta_batch' && Array.isArray(msg.deltas)) {
              handleLiveDeltas(msg.deltas);
            }
          } catch (err) {
            console.debug('[console-stream] Error parsing SSE payload:', err);
          }
        };

        es.onerror = () => {
          consoleWorkspace.sseHealthy = false;
          if (liveBadge) {
            liveBadge.className = 'console-live-badge';
            liveBadge.innerHTML = '<span class="dot" style="background:#f59e0b; box-shadow:none;"></span> Reconectando…';
          }
          pollConsoleMonitors(true);   // sin SSE, el sondeo pasa a ser la fuente
        };

      } catch (err) {
        console.warn('[console-stream] EventSource connection failed:', err);
        pollConsoleMonitors();
      }
    }

    async function pollConsoleMonitors(force) {
      if (!consoleWorkspace.isActiveTab || document.hidden) return;
      /* El SSE ya entrega la instantánea y los deltas.  Este sondeo es la red de
         seguridad para cuando la conexión se cae o se queda muda, y su respuesta
         son ~900 KB (todo el anillo de líneas de 32 servicios): con el SSE sano
         basta un repaso cada 30 s en vez de cada 3 s.  Medido: 20 -> 2
         peticiones por minuto. */
      if (!force && consoleWorkspace.sseHealthy
          && (Date.now() - (consoleWorkspace.lastWallPoll || 0)) < 30000) {
        return;
      }
      consoleWorkspace.lastWallPoll = Date.now();
      const svcsToFetch = [];
      for (const name of consoleWorkspace.monitoredServices) {
        if (!consoleWorkspace.controlMap.has(name)) {
          svcsToFetch.push(name);
        }
      }
      if (svcsToFetch.length === 0) return;

      try {
        const res = await fetch('/api/services/wall');
        if (!res.ok) return;
        const data = await res.json();
        noteServerClock(data.timestamp);
        if (data.services && Array.isArray(data.services)) {
          consoleWorkspace.brokerNames = new Set(data.services.map((s) => s.name));
          entrandoAlMuro();
          data.services.forEach(item => {
            consoleWorkspace.catalogMap.set(item.name, item);
            if (consoleWorkspace.monitoredServices.has(item.name)) {
              updateMonitorPanelContent(item);
            }
          });
        }
      } catch (err) {
        console.debug('[console-workspace] Poll error:', err);
      }
    }

    async function fetchConsoleCatalog() {
      try {
        const res = await fetch('/api/services/catalog');
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data.catalog)) {
          data.catalog.forEach(item => {
            consoleWorkspace.catalogMap.set(item.name, item);
          });
          renderConsoleSidebarServices();
        }
      } catch (err) {
        console.debug('[console-catalog] Error fetching catalog:', err);
      }
    }

    function onConsoleTabActivated() {
      consoleWorkspace.isActiveTab = true;
      entrandoAlMuro();          // 1:1 con el laboratorio: el muro muestra todas las consolas
      applyWallPauseUi();
      applyFocusLayer();
      renderConsoleSidebarServices();
      renderConsoleStage();
      schedulePanelVisibilitySync();
      connectLiveConsoleStream();
      updateLiveClock();

      if (!consoleWorkspace.clockTimer) {
        consoleWorkspace.clockTimer = setInterval(updateLiveClock, 1000);
      }
      if (!consoleWorkspace.pollTimer) {
        consoleWorkspace.pollTimer = setInterval(pollConsoleMonitors, 3000);
      }
    }

    function onConsoleTabDeactivated() {
      consoleWorkspace.isActiveTab = false;
      /* Al salir del muro se suelta todo.  Antes la conexión SSE seguía abierta
         (lo decía el comentario) y los paneles quedaban hidratados: medido, con
         el muro oculto seguía reconstruyéndose DOM invisible (696 → 1051
         líneas) y una pasada de visibilidad costaba 437 ms.  Al volver,
         `onConsoleTabActivated()` reconecta y la instantánea repuebla buffers. */
      if (consoleWorkspace.eventSource) {
        try { consoleWorkspace.eventSource.close(); } catch (_) { /* ya cerrado */ }
        consoleWorkspace.eventSource = null;
      }
      if (consoleWorkspace.clockTimer) {
        clearInterval(consoleWorkspace.clockTimer);
        consoleWorkspace.clockTimer = null;
      }
      if (consoleWorkspace.pollTimer) {
        clearInterval(consoleWorkspace.pollTimer);
        consoleWorkspace.pollTimer = null;
      }
      consoleWorkspace.sseHealthy = false;
      document.querySelectorAll('.console-panel').forEach((panel) => {
        if (panel.dataset.hydrated === '1') dehydratePanel(panel, panel.dataset.service);
      });
    }

    function onServicesUpdatedForConsoleWorkspace() {
      if (!consoleWorkspace.isActiveTab) return;
      /* Con `showAll`, el muro sigue el catálogo: si arrancas un microservicio en
         la pestaña Microservicios, aquí entra su tarjeta y se refresca su
         estado.  Antes sólo se refrescaba la barra lateral, de modo que el muro
         parecía no enterarse. */
      entrandoAlMuro();
      renderConsoleSidebarServices();
      consoleWorkspace.monitoredServices.forEach((svc) => {
        const item = consoleWorkspace.catalogMap.get(svc);
        if (item) updatePanelStatusVisuals(svc, item.status, item.is_standby);
      });
      /* Con "Solo activas", un servicio que acaba de arrancar (o de pararse)
         debe entrar o salir de la rejilla sin esperar a otra acción. */
      if (consoleWorkspace.onlyActive) renderConsoleStage();
    }

    // -------------------------------------------------------------------------
    // Presets and layout controls
    // -------------------------------------------------------------------------
    function applyPresetRunning() {
      const all = getAllServicesList();
      all.forEach(s => {
        if (getServiceStatusState(s) === 'running') {
          consoleWorkspace.monitoredServices.add(s.name);
          if (!consoleWorkspace.followMap.has(s.name)) {
            consoleWorkspace.followMap.set(s.name, true);
          }
        }
      });
      saveConsoleWorkspaceStorage();
      renderConsoleSidebarServices();
      renderConsoleStage();
      showToast('▶ Consolas de servicios activos agregadas.');
    }

    function applyPresetAll() {
      const all = getAllServicesList();
      all.forEach(s => {
        consoleWorkspace.monitoredServices.add(s.name);
        if (!consoleWorkspace.followMap.has(s.name)) {
          consoleWorkspace.followMap.set(s.name, true);
        }
      });
      saveConsoleWorkspaceStorage();
      renderConsoleSidebarServices();
      renderConsoleStage();
      showToast('👁️ Todos los servicios agregados a consolas.');
    }

    async function applyClearMonitors() {
      for (const svc of Array.from(consoleWorkspace.controlMap.keys())) {
        await stopControlMode(svc);
      }
      consoleWorkspace.monitoredServices.clear();
      consoleWorkspace.maximizedService = null;
      saveConsoleWorkspaceStorage();
      renderConsoleSidebarServices();
      renderConsoleStage();
      showToast('❌ Consolas limpiadas.');
    }

    function setConsoleSidebarCollapsed(collapsed) {
      consoleWorkspace.sidebarCollapsed = Boolean(collapsed);
      const workspace = document.getElementById('consoleWorkspace');
      if (workspace) workspace.classList.toggle('is-sidebar-collapsed', consoleWorkspace.sidebarCollapsed);
      const toggleBtn = document.getElementById('btnToggleSidebar');
      if (toggleBtn) {
        toggleBtn.classList.toggle('is-active', consoleWorkspace.sidebarCollapsed);
        toggleBtn.innerText = consoleWorkspace.sidebarCollapsed ? '◨ Servicios' : '◧ Servicios';
      }
      saveConsoleWorkspaceStorage();
      // Column count depends on the available width: re-render once laid out.
      scheduleFrame(() => renderConsoleStage());
    }

    function closeConsoleMoreMenu() {
      const menu = document.getElementById('consoleMoreMenu');
      const btn = document.getElementById('btnConsoleMore');
      if (menu) menu.hidden = true;
      if (btn) btn.setAttribute('aria-expanded', 'false');
      const mm = document.getElementById('consoleMoreMenu');
      if (mm) mm.style.cssText = '';
    }

    // -------------------------------------------------------------------------
    // Wiring
    // -------------------------------------------------------------------------
    function initConsoleWorkspace() {
      loadConsoleWorkspaceStorage();

      consoleWorkspace.monitoredServices.forEach(svc => {
        if (!consoleWorkspace.followMap.has(svc)) {
          consoleWorkspace.followMap.set(svc, true);
        }
      });

      fetchConsoleCatalog();
      updateLiveClock();
      updateRailCounters();

      // Virtualisation triggers: stage scroll and window resize (throttled).
      const stageView = document.getElementById('consoleStageView');
      if (stageView) {
        stageView.addEventListener('scroll', schedulePanelVisibilitySync, { passive: true });
      }
      window.addEventListener('resize', schedulePanelVisibilitySync);

      setConsoleSidebarCollapsed(consoleWorkspace.sidebarCollapsed);
      if (!consoleWorkspace.clockTimer) {
        consoleWorkspace.clockTimer = setInterval(updateLiveClock, 1000);
      }

      const searchInput = document.getElementById('consoleSearchInput');
      if (searchInput) {
        searchInput.addEventListener('input', (e) => {
          consoleWorkspace.searchQuery = e.target.value.trim();
          renderConsoleSidebarServices();
        });
      }

      const catSelect = document.getElementById('consoleCategorySelect');
      if (catSelect) {
        catSelect.addEventListener('change', (e) => {
          consoleWorkspace.categoryFilter = e.target.value || 'all';
          saveConsoleWorkspaceStorage();
          renderConsoleSidebarServices();
        });
      }

      const stateSelect = document.getElementById('consoleFilterSelect');
      if (stateSelect) {
        stateSelect.addEventListener('change', (e) => {
          consoleWorkspace.filter = e.target.value || 'all';
          saveConsoleWorkspaceStorage();
          renderConsoleSidebarServices();
        });
      }

      document.getElementById('btnRefreshCatalog')?.addEventListener('click', () => {
        fetchConsoleCatalog();
        showToast('🔄 Catálogo de servicios actualizado.');
      });

      document.getElementById('btnPresetRunning')?.addEventListener('click', applyPresetRunning);
      document.getElementById('btnPresetAll')?.addEventListener('click', applyPresetAll);
      document.getElementById('btnClearMonitors')?.addEventListener('click', applyClearMonitors);
      document.getElementById('btnEmptyRunning')?.addEventListener('click', applyPresetRunning);
      document.getElementById('btnEmptyAll')?.addEventListener('click', applyPresetAll);
      document.getElementById('btnStageClearAll')?.addEventListener('click', async () => {
        closeConsoleMoreMenu();
        await applyClearMonitors();
      });

      // Sidebar collapse / full-width mode
      document.getElementById('btnToggleSidebar')?.addEventListener('click', () => {
        setConsoleSidebarCollapsed(!consoleWorkspace.sidebarCollapsed);
      });
      document.getElementById('btnExpandSidebar')?.addEventListener('click', () => {
        setConsoleSidebarCollapsed(false);
      });
      document.getElementById('btnMenuHideSidebar')?.addEventListener('click', () => {
        closeConsoleMoreMenu();
        setConsoleSidebarCollapsed(true);
      });
      document.querySelectorAll('#consoleSidebarRail [data-rail-filter]').forEach((btn) => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('#consoleSidebarRail [data-rail-filter]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          consoleWorkspace.filter = btn.dataset.railFilter;
          setConsoleSidebarCollapsed(false);
          renderConsoleSidebarServices();
        });
      });

      // View mode (Mosaico / Pestañas)
      document.getElementById('btnViewMosaic')?.addEventListener('click', () => {
        consoleWorkspace.viewMode = 'mosaic';
        saveConsoleWorkspaceStorage();
        renderConsoleStage();
      });
      document.getElementById('btnViewTabs')?.addEventListener('click', () => {
        consoleWorkspace.viewMode = 'tabs';
        saveConsoleWorkspaceStorage();
        renderConsoleStage();
      });

      // Group mode (secondary; lives inside "Más ⋯")
      document.getElementById('btnGroupFlat')?.addEventListener('click', () => {
        consoleWorkspace.groupMode = 'flat';
        saveConsoleWorkspaceStorage();
        renderConsoleStage();
      });
      document.getElementById('btnGroupCategories')?.addEventListener('click', () => {
        consoleWorkspace.groupMode = 'grouped';
        saveConsoleWorkspaceStorage();
        renderConsoleStage();
      });

      entrandoAlMuro();
      applyWallPauseUi();
      paintFocusButton();
      if (document.body.classList.contains('wall-only')) {
        const pb = document.getElementById('btnWallPopout');
        if (pb) pb.hidden = true;
      }

      const densitySelect = document.getElementById('consoleDensitySelect');
      if (densitySelect) {
        densitySelect.addEventListener('change', (e) => {
          consoleWorkspace.density = e.target.value;
          saveConsoleWorkspaceStorage();
          renderConsoleStage();
        });
      }

      const gridSelect = document.getElementById('consoleGridSelect');
      if (gridSelect) {
        gridSelect.addEventListener('change', (e) => {
          consoleWorkspace.gridCols = e.target.value;
          /* Elegir columnas a mano desactiva el ajuste automático (así la
             migración del valor heredado no pisa una decisión del usuario). */
          consoleWorkspace.gridColsManual = e.target.value !== 'auto';
          saveConsoleWorkspaceStorage();
          renderConsoleStage();
        });
      }

      pintarDestino();
      ajustarFilasDeConsola();
      /* Red de seguridad de la virtualización: si un panel queda deshidratado
         estando a la vista (se veía en negro con el pie en «LIVE»), esta pasada
         lo recupera aunque el servicio no emita líneas nuevas.  Con el muro en
         otra pestaña la propia función suelta el DOM, así que no hay coste. */
      if (!window.__vigilaPanelesVisibles) {
        window.__vigilaPanelesVisibles = setInterval(() => {
          const activo = document.querySelector('.tab-pane.active');
          if (!activo || activo.id !== 'tab-consoles' || document.hidden) return;
          syncPanelVisibility();
          /* Y si un panel visible se quedó sin cuerpo (p. ej. perdió sus líneas
             al deshidratarse), se repinta para que muestre su estado. */
          document.querySelectorAll('#tab-consoles .console-panel').forEach((p) => {
            const b = p.querySelector('.console-monitor-body');
            if (!b || b.querySelector('.console-line, .console-vacio')) return;
            const q = p.getBoundingClientRect();
            if (q.height && q.bottom > 0 && q.top < window.innerHeight) renderPanelBody(p.dataset.service, { force: true });
          });
        }, 2500);
      }
      window.addEventListener('resize', () => {
        clearTimeout(window.__tFilasConsola);
        window.__tFilasConsola = setTimeout(ajustarFilasDeConsola, 200);
      });
      const pestanaMuro = document.querySelector('.sidebar-nav-item[data-tab="consoles"]');
      if (pestanaMuro) pestanaMuro.addEventListener('click', () => setTimeout(ajustarFilasDeConsola, 350));

      // ------------------- controles de la barra del muro -------------------
      const sortSelect = document.getElementById('consoleSortSelect');
      if (sortSelect) {
        sortSelect.value = consoleWorkspace.orderMode;
        sortSelect.addEventListener('change', (e) => {
          consoleWorkspace.orderMode = e.target.value;
          if (e.target.value !== 'manual') consoleWorkspace.orderList = [];
          saveConsoleWorkspaceStorage();
          renderConsoleStage();
          showToast(`↕ Consolas ordenadas por ${e.target.selectedOptions[0].textContent.toLowerCase()}`);
        });
      }

      const tailSelect = document.getElementById('consoleTailSelect');
      if (tailSelect) {
        tailSelect.value = String(consoleWorkspace.tailLines);
        tailSelect.addEventListener('change', (e) => {
          consoleWorkspace.tailLines = parseInt(e.target.value, 10) || 200;
          saveConsoleWorkspaceStorage();
          consoleWorkspace.monitoredServices.forEach((svc) => markPanelDirty(svc));
          scheduleFrame();
        });
      }

      const errToggle = document.getElementById('toggleWallErrors');
      if (errToggle) {
        errToggle.checked = consoleWorkspace.errorsAll === true;
        errToggle.addEventListener('change', (e) => {
          consoleWorkspace.errorsAll = e.target.checked;
          saveConsoleWorkspaceStorage();
          renderConsoleStage();
          showToast(e.target.checked ? '⚠️ Todas las consolas: solo errores' : '↩️ Todas las consolas: sin filtro de errores');
        });
      }

      const actToggle = document.getElementById('toggleWallOnlyActive');
      if (actToggle) {
        actToggle.checked = consoleWorkspace.onlyActive === true;
        actToggle.addEventListener('change', (e) => {
          consoleWorkspace.onlyActive = e.target.checked;
          saveConsoleWorkspaceStorage();
          renderConsoleStage();
          showToast(e.target.checked
            ? '🟢 Muro: solo consolas activas'
            : '↩️ Muro: todas las consolas del catálogo');
        });
      }

      const svcSearch = document.getElementById('consoleServiceSearch');
      if (svcSearch) {
        svcSearch.value = consoleWorkspace.nameFilter || '';
        svcSearch.addEventListener('input', (e) => {
          consoleWorkspace.nameFilter = e.target.value.trim().toLowerCase();
          refrescarBotonLimpiarBusqueda();
          renderConsoleStage();
        });
        refrescarBotonLimpiarBusqueda();
      }

      const chipWrap = document.getElementById('consoleGlobalChips');
      if (chipWrap) {
        chipWrap.querySelectorAll('.cw-chip').forEach((c) => {
          c.classList.toggle('on', (c.dataset.filter || '') === (consoleWorkspace.filterAll || ''));
        });
      }

      const focusBtn = document.getElementById('btnWallFocus');
      if (focusBtn) {
        focusBtn.addEventListener('click', () => {
          if (!consoleWorkspace.focusList.length) {
            showToast('◎ Marca consolas con ⋯ ▸ Añadir a Enfoque (hasta 3)');
            return;
          }
          applyFocusLayer();
          showToast(`◎ ${consoleWorkspace.focusList.length} consola(s) en Enfoque`);
        });
      }

      window.addEventListener('resize', () => {
        consoleWorkspace.monitoredServices.forEach((s) => {
          const panel = document.getElementById(`console-panel-${s}`);
          if (panel && panel.style.display !== 'none' && !consoleWorkspace.controlMap.has(s)) {
            renderPanelBody(s, { force: true });
          }
        });
      });

      const fitBtn = document.getElementById('btnWallFit');
      if (fitBtn) {
        fitBtn.addEventListener('click', () => {
          consoleWorkspace.monitoredServices.forEach((s) => {
            consoleWorkspace.followMap.set(s, true);
            markPanelDirty(s);
          });
          scheduleFrame();
          showToast('↔ Consolas reajustadas y llevadas al final');
        });
      }

      const popoutBtn = document.getElementById('btnWallPopout');
      if (popoutBtn) {
        popoutBtn.addEventListener('click', () => {
          if (document.body.classList.contains('wall-only')) return;   // ya estamos en la ventana del muro
          if (popoutBtn.dataset.abriendo === '1') return;              // evita dobles clics
          if (consoleWorkspace._popout && !consoleWorkspace._popout.closed) {
            consoleWorkspace._popout.focus();
            showToast('⧉ La ventana del muro ya está abierta');
            return;
          }
          popoutBtn.dataset.abriendo = '1';
          const w = window.open('/?tab=consoles&wall=1', 'sisperMuro', 'width=1600,height=900,left=60,top=40');
          setTimeout(() => { delete popoutBtn.dataset.abriendo; }, 1200);
          if (w) {
            consoleWorkspace._popout = w;
            w.focus();
            showToast('⧉ Muro abierto en otra ventana: arrástrala a tu segundo monitor');
          } else {
            showToast('El navegador bloqueó la ventana; permite las ventanas emergentes');
          }
        });
      }

      const pauseBtn = document.getElementById('btnWallPause');
      if (pauseBtn) {
        pauseBtn.addEventListener('click', () => {
          consoleWorkspace.paused = !consoleWorkspace.paused;
          applyWallPauseUi();
          showToast(consoleWorkspace.paused ? 'Ⅱ Muro en pausa (la captura continúa en segundo plano)' : '▶ Muro reanudado');
        });
      }

      const resetBtn = document.getElementById('btnWallReset');
      if (resetBtn) {
        resetBtn.addEventListener('click', () => {
          consoleWorkspace.filterAll = '';
          consoleWorkspace.errorsAll = false;
          consoleWorkspace.queryMap.clear();
          consoleWorkspace.filterMap.clear();
          consoleWorkspace.errorsMap.clear();
          consoleWorkspace.focusList = [];
          consoleWorkspace.focusLayout = 'auto';
          consoleWorkspace.orderMode = 'manual';
          consoleWorkspace.orderList = [];
          consoleWorkspace.paused = false;
          consoleWorkspace.tailLines = 200;
          consoleWorkspace.wallFontSize = 11;
          consoleWorkspace.fontMap.clear();
          const tailSel = document.getElementById('consoleTailSelect'); if (tailSel) tailSel.value = '200';
          const errChk = document.getElementById('toggleWallErrors'); if (errChk) errChk.checked = false;
          const sortSel = document.getElementById('consoleSortSelect'); if (sortSel) sortSel.value = 'manual';
          if (chipWrap) chipWrap.querySelectorAll('.cw-chip').forEach((c) => c.classList.toggle('on', (c.dataset.filter || '') === ''));
          const outSearch = document.getElementById('consoleOutputSearch'); if (outSearch) outSearch.value = '';
          consoleWorkspace.outputSearchQuery = '';
          applyWallPauseUi();
          applyFocusLayer();
          mostrarTodasLasConsolas();
          showToast('↺ Vista del muro restablecida');
        });
      }

      // "Más ⋯" menu
      const moreBtn = document.getElementById('btnConsoleMore');
      const moreMenu = document.getElementById('consoleMoreMenu');
      if (moreBtn && moreMenu) {
        moreBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const willOpen = moreMenu.hidden;
          moreMenu.hidden = !willOpen;
          moreBtn.setAttribute('aria-expanded', String(willOpen));
          if (willOpen) {
            /* La barra y el escenario usan overflow:hidden: si el menú fuera
               absoluto quedaría recortado bajo los terminales. Capa fija. */
            const r = moreBtn.getBoundingClientRect();
            const mr = moreMenu.getBoundingClientRect();
            let left = Math.min(r.right - mr.width, window.innerWidth - mr.width - 8);
            if (left < 8) left = 8;
            let top = r.bottom + 4;
            if (top + mr.height > window.innerHeight - 8) top = Math.max(8, window.innerHeight - 8 - mr.height);
            moreMenu.style.position = 'fixed';
            moreMenu.style.left = left + 'px';
            moreMenu.style.top = top + 'px';
            moreMenu.style.right = 'auto';
            moreMenu.style.zIndex = '120';
          } else {
            moreMenu.style.cssText = '';
          }
        });
        document.addEventListener('click', (e) => {
          if (moreMenu.hidden) return;
          if (!moreMenu.contains(e.target) && e.target !== moreBtn) closeConsoleMoreMenu();
        });
      }

      // Global follow switch
      const followToggle = document.getElementById('toggleGlobalFollow');
      if (followToggle) {
        followToggle.addEventListener('change', (e) => {
          consoleWorkspace.globalFollow = e.target.checked;
          consoleWorkspace.monitoredServices.forEach(s => {
            const pausedPill = document.getElementById(`console-paused-${s}`);
            const jumpBtn = document.getElementById(`console-jump-${s}`);
            if (consoleWorkspace.globalFollow) {
              consoleWorkspace.followMap.set(s, true);
              if (pausedPill) pausedPill.style.display = 'none';
              if (jumpBtn) jumpBtn.hidden = true;
            }
            markPanelDirty(s);
          });
        });
      }

      // Output search (Ctrl+F): highlights matches without re-fetching anything
      const outputSearch = document.getElementById('consoleOutputSearch');
      if (outputSearch) {
        let searchTimer = null;
        outputSearch.addEventListener('input', (e) => {
          const q = e.target.value.trim();
          consoleWorkspace.outputSearchQuery = q;
          clearTimeout(searchTimer);
          searchTimer = setTimeout(() => {
            consoleWorkspace.monitoredServices.forEach((s) => {
              const panel = document.getElementById(`console-panel-${s}`);
              if (panel && panel.dataset.hydrated === '1') renderPanelBody(s, { force: true });
            });
          }, 140);
        });

        window.addEventListener('keydown', (e) => {
          const tabConsoles = document.getElementById('tab-consoles');
          const isConsolesActive = tabConsoles && tabConsoles.classList.contains('active');
          const isInputActive = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);

          // / para enfocar el buscador de microservicios en el muro
          if (e.key === '/' && isConsolesActive && !isInputActive) {
            e.preventDefault();
            const searchInput = document.getElementById('consoleServiceSearch');
            if (searchInput) {
              searchInput.focus();
              searchInput.select();
            }
            return;
          }

          // Tecla 'p' para pausar / reanudar el flujo del muro
          if ((e.key === 'p' || e.key === 'P') && isConsolesActive && !isInputActive && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault();
            consoleWorkspace.paused = !consoleWorkspace.paused;
            applyWallPauseUi();
            showToast(consoleWorkspace.paused ? 'Ⅱ Muro en pausa (la captura continúa en segundo plano)' : '▶ Muro reanudado');
            return;
          }

          // Alt + 2..8 para conmutar columnas del muro
          if (e.altKey && !e.ctrlKey && !e.metaKey && isConsolesActive && e.key >= '2' && e.key <= '8') {
            e.preventDefault();
            const cols = parseInt(e.key, 10);
            consoleWorkspace.gridCols = String(cols);
            const gridSelect = document.getElementById('consoleGridSelect');
            if (gridSelect) gridSelect.value = String(cols);
            saveConsoleWorkspaceStorage();
            renderConsoleStage();
            showToast(`🔲 Rejilla cambiada a ${cols} columnas`);
            return;
          }

          // Ctrl/Cmd + F: Buscar dentro de las consolas
          if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
            if (isConsolesActive) {
              e.preventDefault();
              outputSearch.focus();
              outputSearch.select();
            }
          }

          // Ctrl/Cmd + B: Colapsar / expandir barra lateral (compatibilidad)
          if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
            if (isConsolesActive) {
              e.preventDefault();
              setConsoleSidebarCollapsed(!consoleWorkspace.sidebarCollapsed);
            }
          }

          // Escape: Cierra menús, buscador, maximizado o modo Enfoque
          if (e.key === 'Escape') {
            closeConsoleMoreMenu();
            closePanelMenus();
            const searchInput = document.getElementById('consoleServiceSearch');
            if (searchInput && document.activeElement === searchInput) {
              searchInput.blur();
              if (searchInput.value) {
                searchInput.value = '';
                consoleWorkspace.nameFilter = '';
                renderConsoleStage();
              }
              return;
            }
            const focusLayer = document.getElementById('consoleFocusLayer');
            if (focusLayer && !focusLayer.hidden && consoleWorkspace.focusList.length) {
              consoleWorkspace.focusList = [];
              consoleWorkspace.focusLayout = 'auto';
              saveConsoleWorkspaceStorage();
              applyFocusLayer();
              showToast('↩️ Volviste al muro completo');
              return;
            }
            if (consoleWorkspace.maximizedService) {
              consoleWorkspace.maximizedService = null;
              renderConsoleStage();
            }
          }
        });
      }

      document.getElementById('btnStageLaunchTilix')?.addEventListener('click', async () => {
        closeConsoleMoreMenu();
        if (consoleWorkspace.monitoredServices.size === 0) {
          showToast('ℹ️ No hay servicios monitoreados para abrir en Tilix.');
          return;
        }
        for (const svc of consoleWorkspace.monitoredServices) {
          await openTilixViewer(svc);
        }
      });

      // Los menús de panel se dibujan como capa fija: se cierran al hacer clic fuera,
      // al desplazar la rejilla o al redimensionar la ventana.
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.console-monitor-body')) {
          consoleWorkspace.wheelActive = null;
          document.querySelectorAll('.console-panel.is-wheel-active').forEach((p) => p.classList.remove('is-wheel-active'));
        }
        if (e.target.closest('.cw-menu') || e.target.closest('[data-action="panel-menu"]')) return;
        closePanelMenus();
      });
      window.addEventListener('resize', () => closePanelMenus());
      const gridMuro = document.getElementById('consoleMosaicGrid');
      if (gridMuro) gridMuro.addEventListener('scroll', () => closePanelMenus(), { passive: true });

      // Global delegation for stage actions
      const tabConsoles = document.getElementById('tab-consoles');
      if (tabConsoles) {
        tabConsoles.addEventListener('click', async (e) => {
          const actionBtn = e.target.closest('[data-action]');
          if (!actionBtn) return;

          const action = actionBtn.dataset.action;
          const svc = actionBtn.dataset.service;

          if (action === 'toggle-monitor') {
            if (e.target.tagName !== 'INPUT') {
              const cb = actionBtn.querySelector('input.console-svc-cb')
                || (actionBtn.classList.contains('console-svc-cb') ? actionBtn : null);
              if (cb && e.target !== cb) cb.checked = !cb.checked;
            }
            await toggleMonitoredService(svc);
            return;
          } else if (action === 'take-control') {
            await startControlMode(svc);
            return;
          } else if (action === 'exit-control') {
            await stopControlMode(svc);
            return;
          } else if (action === 'close-panel') {
            if (consoleWorkspace.controlMap.has(svc)) {
              await stopControlMode(svc);
            }
            if (consoleWorkspace.maximizedService === svc) consoleWorkspace.maximizedService = null;
            consoleWorkspace.monitoredServices.delete(svc);
            saveConsoleWorkspaceStorage();
            renderConsoleSidebarServices();
            renderConsoleStage();
            return;
          } else if (action === 'select-tab') {
            consoleWorkspace.activeTab = svc;
            renderConsoleStage();
            return;
          } else if (action === 'open-detail') {
            const port = parseInt(actionBtn.dataset.port || '0', 10);
            await openServiceDetail(svc, port);
            return;
          } else if (action === 'quick-start') {
            const port = parseInt(actionBtn.dataset.port || '0', 10);
            await handleStartOrRestart(svc, port, false);
            return;
          } else if (action === 'quick-restart') {
            await accionServicioReal(svc, 'restart-single');
            return;
          } else if (action === 'quick-stop') {
            await accionServicioReal(svc, 'stop-single');
            return;
          } else if (action === 'toggle-maximize') {
            closePanelMenus();
            if (consoleWorkspace.focusList.length === 1 && consoleWorkspace.focusList[0] === svc) {
              consoleWorkspace.focusList = [];
            } else {
              consoleWorkspace.focusList = [svc];
            }
            saveConsoleWorkspaceStorage();
            applyFocusLayer();
            if (!consoleWorkspace.focusList.length) renderConsoleStage();
            return;
          } else if (action === 'panel-menu') {
            togglePanelMenu(svc);
            return;
          } else if (action === 'panel-search') {
            closePanelMenus();
            const barra = document.getElementById(`console-search-${svc}`);
            if (barra) {
              barra.classList.add('open');
              const input = barra.querySelector('input');
              if (input) { input.value = consoleWorkspace.queryMap.get(svc) || ''; input.focus(); }
            }
            return;
          } else if (action === 'search-close') {
            const barra = document.getElementById(`console-search-${svc}`);
            if (barra) barra.classList.remove('open');
            consoleWorkspace.queryMap.delete(svc);
            consoleWorkspace.matchIndexMap.delete(svc);
            renderPanelBody(svc, { force: true });
            return;
          } else if (action === 'search-next') {
            panelSearchNav(svc, 1);
            return;
          } else if (action === 'search-prev') {
            panelSearchNav(svc, -1);
            return;
          } else if (action === 'panel-errors') {
            const activar = consoleWorkspace.errorsMap.get(svc) !== true;
            consoleWorkspace.errorsMap.set(svc, activar);
            closePanelMenus();
            refreshPanelControls(svc);
            renderPanelBody(svc, { force: true });
            saveConsoleWorkspaceStorage();
            showToast(activar ? `⚠️ ${svc}: mostrando solo errores` : `↩️ ${svc}: sin filtro de errores`);
            return;
          } else if (action === 'panel-filter') {
            const termino = actionBtn.dataset.filter || '';
            const actual = consoleWorkspace.filterMap.get(svc) || '';
            consoleWorkspace.filterMap.set(svc, actual === termino ? '' : termino);
            closePanelMenus();
            refreshPanelControls(svc);
            renderPanelBody(svc, { force: true });
            saveConsoleWorkspaceStorage();
            showToast(consoleWorkspace.filterMap.get(svc) ? `🔎 ${svc}: solo ${termino}` : `🔎 ${svc}: todas las líneas`);
            return;
          } else if (action === 'font-up' || action === 'font-down') {
            const actual = consoleWorkspace.fontMap.get(svc) || consoleWorkspace.wallFontSize;
            setPanelFont(svc, actual + (action === 'font-up' ? 1 : -1));
            return;
          } else if (action === 'clear-panel') {
            closePanelMenus();
            const buf = consoleWorkspace.buffers.get(svc);
            if (buf) buf.length = 0;
            renderPanelBody(svc, { force: true });
            showToast(`🧹 ${svc}: salida limpiada (la captura continúa)`);
            return;
          } else if (action === 'wall-font-up' || action === 'wall-font-down') {
            setWallFont(consoleWorkspace.wallFontSize + (action === 'wall-font-up' ? 1 : -1));
            return;
          } else if (action === 'wall-filter') {
            const termino = actionBtn.dataset.filter || '';
            consoleWorkspace.filterAll = (consoleWorkspace.filterAll === termino) ? '' : termino;
            document.querySelectorAll('#consoleGlobalChips .cw-chip').forEach((c) => {
              c.classList.toggle('on', (c.dataset.filter || '') === consoleWorkspace.filterAll);
            });
            saveConsoleWorkspaceStorage();
            renderConsoleStage();
            showToast(consoleWorkspace.filterAll ? `🔎 Todas las consolas: solo ${consoleWorkspace.filterAll}` : '🔎 Todas las consolas: sin filtro de líneas');
            return;
          } else if (action === 'panel-enfoque') {
            closePanelMenus();
            toggleEnfoque(svc);
            return;
          } else if (action === 'toggle-group-collapse') {
            const grp = actionBtn.dataset.group;
            if (consoleWorkspace.collapsedGroups.has(grp)) {
              consoleWorkspace.collapsedGroups.delete(grp);
            } else {
              consoleWorkspace.collapsedGroups.add(grp);
            }
            renderConsoleStage();
            return;
          } else if (action === 'resume-follow') {
            consoleWorkspace.followMap.set(svc, true);
            const pausedPill = document.getElementById(`console-paused-${svc}`);
            if (pausedPill) pausedPill.style.display = 'none';
            const jumpBtn = document.getElementById(`console-jump-${svc}`);
            if (jumpBtn) jumpBtn.hidden = true;
            /* Sin esto el chip "⏸ pausa por scroll" se quedaba pegado para
               siempre: al reanudar el scroll ya está en el fondo, así que
               onPanelScroll no entra en ninguna rama y nadie lo ocultaba. */
            const scrollChip = document.getElementById(`console-scrollpause-${svc}`);
            if (scrollChip) scrollChip.hidden = true;
            const statusBack = document.getElementById(`console-footer-status-${svc}`);
            if (statusBack) statusBack.style.display = '';
            const bodyElem = document.getElementById(`console-monitor-body-${svc}`);
            ConsoleViewport.scrollToBottom(bodyElem);
            return;
          }
        });
      }
    }

    async function openServiceDetail(serviceName, port) {
      const res = await fetch(`/api/service/info?service=${serviceName}&port=${port}`);
      if (!res.ok) return;
      const data = await res.json();
      document.getElementById('serviceModalTitle').innerText = `${data.name} (Puerto :${data.port})`;
      document.getElementById('serviceModalBody').innerHTML = `
        <p><strong>Tipo:</strong> ${data.group}</p>
        <p><strong>Ruta:</strong> <code style="font-family:ui-monospace, monospace; color:var(--accent);">${data.path}</code></p>
        <p><strong>Estado en Vivo:</strong> ${data.online ? '<span style="color:var(--success); font-weight:700;">🟢 Activo</span> (PIDs: ' + data.pid + ')' : '<span style="color:var(--danger); font-weight:700;">🔴 Apagado</span>'}</p>
        <p><strong>Rama Git:</strong> 🌿 ${data.git.branch}</p>
        <p><strong>Archivos pendientes (dirty):</strong> ${data.git.dirty > 0 ? '<span style="color:var(--warn); font-weight:700;">' + data.git.dirty + ' archivos</span>' : '0 (Limpio)'}</p>
        <p><strong>Commits locales por subir (ahead):</strong> ${data.git.ahead}</p>
      `;
      document.getElementById('serviceModal').style.display = 'flex';
    }
    function closeServiceModal() { document.getElementById('serviceModal').style.display = 'none'; }

    // -------------------------------------------------------------------------
    // Matriz de Infraestructura & Servicios Institucionales
    // -------------------------------------------------------------------------
    let currentInfraView = 'all';
    const infraProbeResults = {};

    // Destinos de infraestructura por entorno.  Viven en config/panel.json
    // (``infra_targets``) y se cargan desde la API: el código no debe llevar
    // direcciones internas ni comandos de una instalación concreta.
    // Forma de cada entrada:
    //   { id, name, type, target, localKey?, k8sPod?, testUrl?, note, cmd }
    let INFRA_ENDPOINTS = {};
    let infraEndpointsLoaded = false;

    async function loadInfraEndpoints() {
      if (infraEndpointsLoaded) return INFRA_ENDPOINTS;
      infraEndpointsLoaded = true;
      try {
        const res = await fetch('/api/infra/targets');
        if (res.ok) {
          const data = await res.json();
          INFRA_ENDPOINTS = data.environments || {};
        }
      } catch (e) {
        console.error('No se pudieron cargar los destinos de infraestructura:', e);
      }
      return INFRA_ENDPOINTS;
    }

    function copyCmd(cmd) {
      navigator.clipboard.writeText(cmd);
      showToast("Comando copiado al portapapeles: " + cmd);
    }

    function setInfraView(view) {
      currentInfraView = view;
      ['all', 'local', 'develop', 'test', 'prod'].forEach(v => {
        const btn = document.getElementById('infraTab_' + v);
        if (btn) {
          if (v === view) {
            btn.classList.add('active');
            btn.style.background = '#2563eb';
            btn.style.color = '#fff';
          } else {
            btn.classList.remove('active');
            btn.style.background = 'transparent';
            btn.style.color = 'var(--text-muted)';
          }
        }
      });
      renderInfraMatrix();
    }

    function getLiveStatusBadge(env, item, badgeId) {
      if (item.localKey && globalData && globalData.infra && globalData.infra[item.localKey]) {
        const kObj = globalData.infra[item.localKey];
        const isUp = kObj.port_open;
        const containerStr = kObj.container ? (' (' + kObj.container + ')') : '';
        return `<span id="${badgeId}" class="status-badge ${isUp ? 'online' : 'offline'}" style="font-size:10px;"><span class="dot"></span> ${isUp ? ('Activo' + containerStr) : 'Apagado'}</span>`;
      } else if (item.k8sPod && globalData && globalData.infra && globalData.infra.k8s_infra && globalData.infra.k8s_infra[env]) {
        const podSt = globalData.infra.k8s_infra[env][item.k8sPod];
        if (podSt === 'Running') {
          return `<span id="${badgeId}" class="status-badge online" style="font-size:10px;"><span class="dot"></span> Pod (${podSt})</span>`;
        } else if (podSt) {
          return `<span id="${badgeId}" class="status-badge warn" style="font-size:10px;"><span class="dot"></span> Pod (${podSt})</span>`;
        } else {
          return `<span id="${badgeId}" class="status-badge offline" style="font-size:10px;"><span class="dot"></span> Sin Pod</span>`;
        }
      }
      const cacheKey = `${env}_${item.id}`;
      if (infraProbeResults[cacheKey]) {
        const r = infraProbeResults[cacheKey];
        return `<span id="${badgeId}" class="status-badge ${r.online ? 'online' : 'offline'}" style="font-size:10px;"><span class="dot"></span> ${r.text}</span>`;
      }
      if (item.testUrl) {
        return `<span id="${badgeId}" class="status-badge" style="font-size:10px; background:rgba(255,255,255,0.06); color:var(--text-muted);"><span class="dot" style="background:#64748b;"></span> Sin Probar</span>`;
      }
      return `<span id="${badgeId}" class="status-badge" style="font-size:10px; background:rgba(255,255,255,0.04); color:#64748b;">Interno</span>`;
    }

    async function renderInfraMatrix() {
      const container = document.getElementById('infraMatrixContainer');
      if (!container) return;

      await loadInfraEndpoints();
      container.innerHTML = '';

      if (!Object.keys(INFRA_ENDPOINTS).length) {
        container.innerHTML = '<div style="padding:16px; font-size:12px; color:var(--text-muted);">'
          + 'Sin destinos de infraestructura configurados. Defínelos en '
          + '<code>config/panel.json</code> → <code>infra_targets</code>.</div>';
        return;
      }

      if (currentInfraView === 'all') {
        const table = document.createElement('table');
        table.className = 'table';
        table.style = "width:100%; border-collapse:collapse; font-size:12px; border:1px solid #1f2937; border-radius:8px; overflow:hidden;";

        // Las columnas salen de los entornos realmente configurados, no de una
        // lista fija: una instalación con otros nombres de entorno funciona sin
        // tocar el código.
        const envs = Object.keys(INFRA_ENDPOINTS);
        const envLabel = { local: '💻 LOCAL', develop: '🟡 DEVELOP', test: '🔵 TEST', prod: '🟢 PROD', main: '🟢 MAIN' };
        const envColor = { local: '#38bdf8', develop: '#facc15', test: '#60a5fa', prod: '#4ade80', main: '#4ade80' };
        const envColWidth = (78 / envs.length).toFixed(2);
        const baseItems = INFRA_ENDPOINTS.local || INFRA_ENDPOINTS[envs[0]] || [];

        const thead = document.createElement('thead');
        thead.innerHTML = `
          <tr style="background:#0f172a; border-bottom:2px solid #1f2937; text-align:left;">
            <th style="padding:10px 14px; width:22%; color:#f8fafc; font-weight:700;">SERVICIO / COMPONENTE</th>
            ${envs.map(e => `<th style="padding:10px 12px; width:${envColWidth}%; color:${envColor[e] || '#94a3b8'}; font-weight:700;">${envLabel[e] || e.toUpperCase()}</th>`).join('')}
          </tr>
        `;
        table.appendChild(thead);

        const tbody = document.createElement('tbody');

        const infraIconMap = {
          postgres: getTechIcon('postgresql', 18),
          mongo: getTechIcon('mongodb', 18),
          keycloak: getTechIcon('keycloak', 18),
          keydb: getTechIcon('redis', 18),
          rabbitmq: getTechIcon('rabbitmq', 18),
          alfresco: getTechIcon('alfresco', 18),
          onlyoffice: getTechIcon('onlyoffice', 18),
          firmador: getTechIcon('firmador', 18)
        };

        baseItems.forEach((baseItem, idx) => {
          const tr = document.createElement('tr');
          tr.style = "border-bottom:1px solid #1f2937; transition:background 0.15s ease;";
          tr.onmouseenter = () => tr.style.background = 'rgba(255,255,255,0.02)';
          tr.onmouseleave = () => tr.style.background = 'transparent';

          const svcIcon = infraIconMap[baseItem.id] || '';
          const cleanName = baseItem.name.replace(' Local', '').replace(/^[\u{10000}-\u{10FFFF}\u2600-\u27BF\uFE0F\s]+/u, '');

          let rowHtml = `
            <td style="padding:10px 14px; vertical-align:middle;">
              <div style="font-weight:700; font-size:13px; color:#f8fafc; display:flex; align-items:center; gap:8px;">
                ${svcIcon}
                <span>${cleanName}</span>
              </div>
              <div style="font-size:11px; color:var(--text-muted); margin-left:26px;">${baseItem.type}</div>
            </td>
          `;

          envs.forEach(env => {
            // Búsqueda por id y no por índice: si un entorno lista los destinos
            // en otro orden, el índice mostraría la dirección de un servicio
            // bajo el nombre de otro, que en un panel de infraestructura es un
            // error grave.
            const item = (INFRA_ENDPOINTS[env] || []).find(x => x.id === baseItem.id);
            if (!item) {
              rowHtml += '<td style="padding:8px 12px; vertical-align:middle; border-left:1px solid rgba(255,255,255,0.04);"><span style="font-size:11px; color:var(--text-muted);">—</span></td>';
              return;
            }
            const badgeId = `infraStatus_${env}_${item.id}`;
            const liveBadge = getLiveStatusBadge(env, item, badgeId);

            let actionBtns = '';
            if (item.testUrl) {
              actionBtns += `<button class="btn btn-sm btn-outline" style="font-size:9px; padding:1px 5px; height:20px; line-height:1;" onclick="testSingleEndpoint('${env}', '${item.id}', '${item.testUrl}')" title="Probar conexión web">🌐</button>`;
            }
            if (item.cmd) {
              actionBtns += `<button class="btn btn-sm btn-outline" style="font-size:9px; padding:1px 5px; height:20px; line-height:1;" onclick="copyCmd('${item.cmd}')" title="Copiar comando de prueba">📋</button>`;
            }

            rowHtml += `
              <td style="padding:8px 12px; vertical-align:middle; border-left:1px solid rgba(255,255,255,0.04);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:4px; margin-bottom:4px;">
                  <div>${liveBadge}</div>
                  <div style="display:flex; gap:3px;">${actionBtns}</div>
                </div>
                <div>
                  <code style="font-family:ui-monospace, monospace; font-size:10px; background:#0f172a; padding:2px 5px; border-radius:4px; color:#38bdf8; word-break:break-all; border:1px solid #1e293b; display:inline-block;">${item.target}</code>
                </div>
              </td>
            `;
          });

          tr.innerHTML = rowHtml;
          tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        container.appendChild(table);

      } else {
        const grid = document.createElement('div');
        grid.style = "display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:12px;";

        const infraIconMap = {
          postgres: getTechIcon('postgresql', 18),
          mongo: getTechIcon('mongodb', 18),
          keycloak: getTechIcon('keycloak', 18),
          keydb: getTechIcon('redis', 18),
          rabbitmq: getTechIcon('rabbitmq', 18),
          alfresco: getTechIcon('alfresco', 18),
          onlyoffice: getTechIcon('onlyoffice', 18),
          firmador: getTechIcon('firmador', 18)
        };

        const items = INFRA_ENDPOINTS[currentInfraView] || [];
        items.forEach(item => {
          const badgeId = `infraStatus_${currentInfraView}_${item.id}`;
          const liveBadge = getLiveStatusBadge(currentInfraView, item, badgeId);

          const card = document.createElement('div');
          card.style = "background:rgba(17,24,39,0.7); border:1px solid #1f2937; border-radius:10px; padding:12px 14px; display:flex; flex-direction:column; justify-content:space-between; gap:10px; transition:border 0.2s;";

          let testBtn = item.testUrl
            ? `<button class="btn btn-sm btn-outline" style="font-size:10px; padding:2px 8px;" onclick="testSingleEndpoint('${currentInfraView}', '${item.id}', '${item.testUrl}')">🌐 Probar Web</button>`
            : '';

          let copyBtn = item.cmd
            ? `<button class="btn btn-sm btn-outline" style="font-size:10px; padding:2px 8px;" onclick="copyCmd('${item.cmd}')">📋 Copiar Test</button>`
            : '';

          const svcIcon = infraIconMap[item.id] || '';
          const cleanName = item.name.replace(/^[\u{10000}-\u{10FFFF}\u2600-\u27BF\uFE0F\s]+/u, '');

          card.innerHTML = `
            <div>
              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                <div>
                  <strong style="font-size:13px; color:#f8fafc; display:flex; align-items:center; gap:8px;">
                    ${svcIcon}
                    <span>${cleanName}</span>
                  </strong>
                  <div style="font-size:10px; color:var(--text-muted); margin-left:26px;">${item.type}</div>
                </div>
                <div>${liveBadge}</div>
              </div>
              <div style="margin-top:6px; margin-bottom:6px;">
                <code style="font-family:ui-monospace, monospace; font-size:11px; background:#0f172a; padding:3px 8px; border-radius:5px; color:#38bdf8; word-break:break-all; display:inline-block; border:1px solid #1e293b;">${item.target}</code>
              </div>
              <div style="font-size:11px; color:#94a3b8; line-height:1.4;">${item.note}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center; justify-content:flex-end; border-top:1px solid rgba(255,255,255,0.05); padding-top:8px; margin-top:4px;">
              ${testBtn}
              ${copyBtn}
            </div>
          `;
          grid.appendChild(card);
        });

        container.appendChild(grid);
      }

      setTimeout(() => probeClientEndpoints(false), 200);
    }

    async function testSingleEndpoint(env, id, url) {
      const badgeId = `infraStatus_${env}_${id}`;
      const badge = document.getElementById(badgeId);
      if (badge) {
        badge.className = 'status-badge';
        badge.style = "font-size:10px; background:#1e293b; color:#93c5fd;";
        badge.innerHTML = 'Probando...';
      }

      const cacheKey = `${env}_${id}`;
      const startTime = Date.now();
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);
        await fetch(url, { mode: 'no-cors', signal: controller.signal });
        clearTimeout(timeoutId);
        const elapsed = Date.now() - startTime;
        infraProbeResults[cacheKey] = { online: true, text: `Accesible (${elapsed}ms)` };
        if (badge) {
          badge.className = 'status-badge online';
          badge.style = "font-size:10px;";
          badge.innerHTML = `<span class="dot"></span> Accesible (${elapsed}ms)`;
        }
      } catch (err) {
        infraProbeResults[cacheKey] = { online: false, text: 'Sin respuesta' };
        if (badge) {
          badge.className = 'status-badge offline';
          badge.style = "font-size:10px;";
          badge.innerHTML = `<span class="dot"></span> Sin respuesta`;
        }
      }
    }

    async function probeClientEndpoints(showToastFlag = true) {
      if (showToastFlag) {
        const label = currentInfraView === 'all' ? 'TODOS LOS ENTORNOS' : currentInfraView.toUpperCase();
        showToast(`Verificando conectividad web (${label})...`);
      }

      const targets = [];
      if (currentInfraView === 'all') {
        ['local', 'develop', 'test', 'prod'].forEach(env => {
          (INFRA_ENDPOINTS[env] || []).forEach(item => {
            if (item.testUrl) targets.push({ env, id: item.id, url: item.testUrl });
          });
        });
      } else {
        (INFRA_ENDPOINTS[currentInfraView] || []).forEach(item => {
          if (item.testUrl) targets.push({ env: currentInfraView, id: item.id, url: item.testUrl });
        });
      }

      targets.forEach(t => testSingleEndpoint(t.env, t.id, t.url));
    }

    // =========================================================================
    // MAPA OPERATIVO & CONEXIONES ACTIVAS REALES (KEYCLOAK SSO)
    // =========================================================================
    let operationalMapData = null;
    let selectedOperationalZoneId = 1; // Default: I Zona Naval (Valparaíso)
    let currentOperationalMapEnv = 'develop';
    let mapAutoRefreshInterval = null;
    let reparticionSearchTerm = '';

    function setOperationalMapEnv(env) {
      currentOperationalMapEnv = env;
      const sel = document.getElementById('mapEnvSelect');
      if (sel) sel.value = env;
      operationalMapData = null; // Clear old env data immediately so previous environment numbers don't persist
      const kpiRow = document.getElementById('mapKpiSummaryRow');
      if (kpiRow) {
        kpiRow.innerHTML = `<div style="grid-column: 1 / -1; padding: 18px; text-align: center; color: #38bdf8; font-weight: 700; background: rgba(15,23,42,0.6); border: 1px dashed rgba(56,189,248,0.3); border-radius: 10px;">
          🔄 Cargando conexiones Keycloak SSO para entorno <strong>${(env || '').toUpperCase()}</strong>...
        </div>`;
      }
      fetchOperationalMapData(true);
    }

    function toggleMapAutoRefresh(enabled) {
      if (mapAutoRefreshInterval) {
        clearInterval(mapAutoRefreshInterval);
        mapAutoRefreshInterval = null;
      }
      if (enabled) {
        mapAutoRefreshInterval = setInterval(() => {
          const tabMap = document.getElementById('tab-map');
          if (tabMap && tabMap.classList.contains('active')) {
            fetchOperationalMapData(false);
          }
        }, 30000);
      }
    }

    async function fetchOperationalMapData(forceRefresh = false) {
      const spinner = document.getElementById('mapRefreshSpinner');
      if (spinner) spinner.style.display = 'inline-block';

      try {
        const sel = document.getElementById('mapEnvSelect');
        const envParam = (sel ? sel.value : currentOperationalMapEnv) || 'develop';
        currentOperationalMapEnv = envParam;

        const url = `/api/analytics/connections?env=${encodeURIComponent(envParam)}&refresh=${forceRefresh ? 'true' : 'false'}&_t=${Date.now()}`;
        const resp = await fetch(url, { cache: 'no-store' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        operationalMapData = data;

        // Auto-select zone if currently selected zone has no connections or doesn't exist
        if (data.zones && data.zones.length > 0) {
          if (selectedOperationalZoneId !== 'all') {
            const curZone = data.zones.find(z => z.id === selectedOperationalZoneId);
            if (!curZone || curZone.total_connections === 0) {
              if (data.top_zone && data.top_zone.id !== undefined && data.top_zone.connections > 0) {
                selectedOperationalZoneId = data.top_zone.id;
              } else {
                selectedOperationalZoneId = 'all';
              }
            }
          }
        }

        // Keycloak SSO Status Badge
        const kcBadge = document.getElementById('mapKcStatusBadge');
        if (kcBadge) {
          const dbHostStr = (data.db && data.db.host) ? ` | BD: ${data.db.host}:${data.db.port || 5432}` : '';
          const ingressStr = data.env_ip ? ` | GW: ${data.env_ip}` : '';
          const usersStr = `${data.unique_users || data.total_connections} personas (${data.total_connections} ses.)`;
          if (data.keycloak && data.keycloak.status === 'online') {
            kcBadge.innerHTML = `🔑 SSO ${data.env_name || envParam.toUpperCase()}: ${usersStr} (${data.keycloak.latency_ms}ms)${ingressStr}${dbHostStr}`;
            kcBadge.style.color = '#34d399';
            kcBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
          } else {
            kcBadge.innerHTML = `🔴 SSO Keycloak Offline (${envParam.toUpperCase()})${dbHostStr}`;
            kcBadge.style.color = '#ef4444';
            kcBadge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
          }
        }

        const updatedLabel = document.getElementById('mapCoordinatesLabel');
        if (updatedLabel) updatedLabel.innerText = `ACT: ${(data.timestamp || '').split(' ')[1] || data.timestamp} • ${data.env_name || envParam.toUpperCase()}`;

        renderOperationalMapKpis();
        await renderOperationalMapSvg();
        renderOperationalZoneDetail();
      } catch (err) {
        console.error('Error fetching operational map data:', err);
        showToast('Error cargando conexiones del mapa: ' + err.message);
      } finally {
        if (spinner) spinner.style.display = 'inline';
      }
    }

    function renderOperationalMapKpis() {
      const container = document.getElementById('mapKpiSummaryRow');
      if (!container || !operationalMapData) return;

      const totalUsers = operationalMapData.unique_users || 0;
      const totalSessions = operationalMapData.total_connections || 0;
      const subtitleTotal = `${totalSessions} sesiones SSO activas • ${operationalMapData.env_name || ''}`;
      const isAllSelected = (selectedOperationalZoneId === 'all');
      const glowAll = isAllSelected ? 'box-shadow: 0 0 16px rgba(56,189,248,0.5); border-width:2px;' : '';

      const peakData = operationalMapData.peak_connections || { count: totalSessions, unique_users: totalUsers, timestamp: '' };
      const peakHtml = (peakData.unique_users > 0 || peakData.count > 0) ? `
        <div style="margin-top:6px; padding-top:4px; border-top:1px dashed rgba(255,255,255,0.12); font-size:10.5px; color:#f59e0b; display:flex; align-items:center; justify-content:space-between; gap:4px;">
          <span>🔥 <strong>Peak:</strong> ${peakData.unique_users || peakData.count} personas (${peakData.count || 0} ses.)</span>
          <span style="font-size:9.5px; color:var(--text-muted);">${(peakData.timestamp || '').split(' ')[0]}</span>
        </div>
      ` : '';

      let cardsHtml = `
        <div class="panel-box" style="cursor:pointer; border-color:${isAllSelected ? '#38bdf8' : 'rgba(56,189,248,0.4)'}; background:rgba(15,23,42,0.85); ${glowAll} transition:all 0.2s; min-width:195px; flex:1 1 195px; overflow:hidden;" onclick="selectOperationalZone('all')">
          <div class="panel-box-header">
            <span class="panel-box-title" style="color:#38bdf8; font-size:12px; white-space:nowrap;">🇨🇱 TOTAL PERSONAS</span>
          </div>
          <div style="font-size:24px; font-weight:800; color:#fff; margin:4px 0;">${totalUsers} <span style="font-size:12px; color:#38bdf8; font-weight:600;">personas</span></div>
          <span style="font-size:11px; color:var(--text-muted);">${subtitleTotal}</span>
          ${peakHtml}
        </div>
      `;

      (operationalMapData.zones || []).forEach(z => {
        const isSelected = (z.id === selectedOperationalZoneId);
        const userCount = z.unique_users || 0;
        const connCount = z.total_connections || 0;
        const borderColor = isSelected ? z.color : (userCount > 0 ? `${z.color}80` : 'var(--card-border)');
        const glow = isSelected ? `box-shadow: 0 0 14px ${z.color}40; border-width:2px;` : '';
        cardsHtml += `
          <div class="panel-box" style="cursor:pointer; border-color:${borderColor}; ${glow} transition:all 0.2s; ${userCount > 0 ? 'background:rgba(15,23,42,0.9);' : 'opacity:0.75;'}" onclick="selectOperationalZone(${z.id})">
            <div class="panel-box-header">
              <span class="panel-box-title" style="color:${z.color}; font-size:11px;">${z.sigla}</span>
              <span style="font-size:10px; font-weight:800; color:${userCount > 0 ? z.color : '#64748b'};">${z.percentage}%</span>
            </div>
            <div style="font-size:20px; font-weight:800; color:${userCount > 0 ? '#fff' : '#64748b'}; margin:3px 0;">${userCount} <span style="font-size:11px; font-weight:normal; color:var(--text-muted);">personas</span></div>
            <span style="font-size:11px; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${connCount} sesiones • ${z.sede}</span>
          </div>
        `;
      });

      container.innerHTML = cardsHtml;
    }

    function selectOperationalZone(zoneId) {
      selectedOperationalZoneId = zoneId;
      reparticionSearchTerm = '';
      renderOperationalMapKpis();
      renderOperationalMapSvg();
      renderOperationalZoneDetail();
    }

    let chileSvgLoadingPromise = null;

    async function ensureChileMapSvgLoaded() {
      const container = document.getElementById('svgChileMapContainer');
      if (!container) return false;
      if (container.querySelector('svg')) return true;

      if (!chileSvgLoadingPromise) {
        chileSvgLoadingPromise = fetch('/api/map/chile_svg?_t=' + Date.now())
          .then(res => {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.text();
          })
          .then(svgText => {
            container.innerHTML = svgText;
            return true;
          })
          .catch(err => {
            console.error('Error cargando mapa vectorial de Chile:', err);
            container.innerHTML = '<div style="color:#ef4444; padding:20px; text-align:center;">Error cargando mapa vectorial geográfico de Chile.</div>';
            return false;
          });
      }
      return await chileSvgLoadingPromise;
    }

    async function renderOperationalMapSvg() {
      const container = document.getElementById('svgChileMapContainer');
      if (!container || !operationalMapData) return;

      const loaded = await ensureChileMapSvgLoaded();
      if (!loaded) return;

      const zones = operationalMapData.zones || [];
      const zMap = {};
      zones.forEach(z => { zMap[z.id] = z; });

      zones.forEach(z => {
        const isDirectSelected = (z.id === selectedOperationalZoneId);
        const isAllSelected = (selectedOperationalZoneId === 'all');
        const paths = container.querySelectorAll(`.zone-path-${z.id}`);
        paths.forEach(p => {
          if (isAllSelected) {
            if (z.total_connections > 0) {
              p.setAttribute('fill', `${z.color}55`);
              p.setAttribute('stroke', z.color);
              p.setAttribute('stroke-width', '1.2');
              p.style.filter = 'url(#zoneGlow)';
            } else {
              p.setAttribute('fill', `${z.color}35`);
              p.setAttribute('stroke', z.color);
              p.setAttribute('stroke-width', '0.8');
              p.style.filter = 'none';
            }
          } else if (isDirectSelected) {
            p.setAttribute('fill', `${z.color}55`);
            p.setAttribute('stroke', z.color);
            p.setAttribute('stroke-width', '1.3');
            p.style.filter = 'url(#zoneGlow)';
          } else if (z.total_connections > 0) {
            p.setAttribute('fill', `${z.color}25`);
            p.setAttribute('stroke', z.color);
            p.setAttribute('stroke-width', '0.7');
            p.style.filter = 'none';
          } else {
            p.setAttribute('fill', '#1e293b');
            p.setAttribute('stroke', `${z.color}70`);
            p.setAttribute('stroke-width', '0.5');
            p.style.filter = 'none';
          }
        });

        // Update Callout HUD labels
        const lbl = container.querySelector('#svg-conn-label-' + z.id);
        if (lbl) {
          lbl.textContent = `${z.unique_users || 0} Personas (${z.total_connections || 0} Ses.)`;
        }

        // Highlight Callout HUD boxes
        const calloutRect = container.querySelector(`[onclick="selectOperationalZone(${z.id})"] rect`);
        if (calloutRect) {
          calloutRect.setAttribute('stroke-width', isDirectSelected ? '1.8' : (isAllSelected && z.total_connections > 0 ? '1.2' : '0.8'));
          calloutRect.setAttribute('stroke', isDirectSelected ? '#fff' : (z.color || '#334155'));
          calloutRect.setAttribute('fill', isDirectSelected ? 'rgba(30,41,59,0.95)' : 'rgba(15,23,42,0.85)');
        }
      });
    }

    function renderOperationalZoneDetail() {
      const container = document.getElementById('zoneDetailPanel');
      if (!container || !operationalMapData) return;

      const zones = operationalMapData.zones || [];
      const totalAllConns = operationalMapData.total_connections || 0;
      const totalAllUsers = operationalMapData.unique_users || 0;
      const allActiveReps = operationalMapData.all_active_reparticiones || [];

      // -----------------------------------------------------------------------
      // VISTA A: TOTAL CONEXIONES NACIONAL (selectedOperationalZoneId === 'all')
      // -----------------------------------------------------------------------
      if (selectedOperationalZoneId === 'all') {
        const q = (reparticionSearchTerm || '').trim().toLowerCase();
        const filteredAll = q 
          ? allActiveReps.filter(r => r.sigla.toLowerCase().includes(q) || r.desc.toLowerCase().includes(q) || String(r.cod).includes(q) || (r.zona_sigla && r.zona_sigla.toLowerCase().includes(q)))
          : allActiveReps;

        let html = `
          <!-- Header Nacional -->
          <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid var(--card-border); padding-bottom:14px; flex-wrap:wrap; gap:10px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="badge-pill" style="background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid #38bdf8; font-size:12px; font-weight:800;">🇨🇱 TODAS LAS ZONAS • NACIONAL</span>
                <h3 style="margin:0; font-size:17px; font-weight:800; color:#fff;">Despliegue Nacional de Personas Conectadas</h3>
              </div>
              <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
                📍 Ámbito: <strong style="color:#f8fafc;">Consolidado de Todas las Jurisdicciones y Zonas Navales</strong>
              </div>
              <div style="font-size:11px; color:#64748b; margin-top:2px;">
                🛡️ Cobertura: Territorio Nacional Continental, Insular, Antártico y Misiones en el Extranjero
              </div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:26px; font-weight:900; color:#38bdf8;">${totalAllUsers} <span style="font-size:13px; font-weight:normal; color:#cbd5e1;">Personas</span></div>
              <div style="font-size:11px; color:var(--text-muted);">${totalAllConns} Sesiones SSO Activas (${operationalMapData.env_name || ''})</div>
            </div>
          </div>

          <!-- Distribución Resumen por Zonas Navales -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span style="font-size:12px; font-weight:800; color:#fff; text-transform:uppercase; letter-spacing:0.5px;">⚓ Distribución por Jurisdicción / Zona Naval</span>
              <span style="font-size:11px; color:var(--text-muted);">Haz clic en una zona para filtrar su territorio</span>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px;">
              ${zones.map(z => `
                <div onclick="selectOperationalZone(${z.id})" style="cursor:pointer; background:rgba(15,23,42,0.7); border:1px solid ${z.unique_users > 0 ? z.color + '60' : 'rgba(255,255,255,0.06)'}; border-radius:8px; padding:8px 10px; transition:transform 0.15s, border-color 0.2s;" onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='none'">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; color:${z.color}; font-size:11px;">${z.sigla}</span>
                    <span style="font-size:10px; font-weight:700; color:${z.unique_users > 0 ? z.color : '#64748b'};">${z.percentage}%</span>
                  </div>
                  <div style="font-size:16px; font-weight:800; color:${z.unique_users > 0 ? '#fff' : '#64748b'}; margin:2px 0;">
                    ${z.unique_users || 0} <span style="font-size:10px; font-weight:normal; color:var(--text-muted);">personas</span>
                  </div>
                  <div style="font-size:10px; color:var(--text-muted); display:flex; justify-content:space-between;">
                    <span>${z.total_connections || 0} ses. • ${(z.reparticiones || []).length} reps</span>
                    <span style="color:${z.color};">Ver ➔</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Catálogo Nacional Completo de Reparticiones -->
          <div style="display:flex; flex-direction:column; gap:10px; margin-top:6px; flex:1;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:12px; font-weight:800; color:#fff; text-transform:uppercase; letter-spacing:0.5px;">📋 Todas las Reparticiones Activas a Nivel Nacional (${allActiveReps.length})</span>
                <span class="badge-pill badge-clean" style="font-size:10px;">${filteredAll.length} visibles</span>
              </div>
              <input type="text" class="search-input" placeholder="🔍 Filtrar por sigla, nombre o zona..." 
                     value="${escapeHtml(reparticionSearchTerm)}" 
                     oninput="onSearchZoneReparticiones(this.value)" 
                     style="max-width:280px; font-size:11px; padding:6px 10px;">
            </div>

            <div style="max-height:400px; overflow-y:auto; border:1px solid var(--card-border); border-radius:10px;">
              <table class="reparticion-table">
                <thead>
                  <tr>
                    <th style="width:60px;">Código</th>
                    <th style="width:75px;">Zona</th>
                    <th style="width:110px;">Sigla</th>
                    <th>Denominación Oficial</th>
                    <th style="width:85px; text-align:right;">Personas</th>
                    <th style="width:85px; text-align:right;">Sesiones</th>
                    <th style="width:70px; text-align:right;">% Total</th>
                    <th style="width:95px; text-align:center;">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  ${filteredAll.length === 0 ? `
                    <tr>
                      <td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);">
                        ${allActiveReps.length === 0 ? 'No se registran conexiones activas en este entorno.' : 'No se encontraron reparticiones coincidentes.'}
                      </td>
                    </tr>
                  ` : filteredAll.map(r => `
                    <tr>
                      <td style="font-family:monospace; color:#64748b;">${r.cod}</td>
                      <td>
                        <span class="badge-pill" style="background:${r.zona_color}20; color:${r.zona_color}; border:1px solid ${r.zona_color}50; font-size:10px; padding:1px 6px;">${r.zona_sigla}</span>
                      </td>
                      <td>
                        <strong style="color:var(--accent); cursor:pointer; text-decoration:underline; font-size:12px;" onclick="openReparticionUsersModal('${r.cod}', '${r.sigla}')" title="Ver usuarios conectados en ${r.sigla}">${r.sigla}</strong>
                      </td>
                      <td style="color:#cbd5e1; font-size:11px;">${r.desc}</td>
                      <td style="text-align:right; font-weight:800; font-family:monospace; color:#38bdf8;">${r.users}</td>
                      <td style="text-align:right; color:#94a3b8; font-size:11px;">${r.connections}</td>
                      <td style="text-align:right; color:var(--text-muted); font-size:10px;">${r.pct_nacional}%</td>
                      <td style="text-align:center;">
                        <button class="btn btn-sm btn-outline" style="padding:2px 7px; font-size:10px; border-color:rgba(56,189,248,0.4); color:#38bdf8;" onclick="openReparticionUsersModal('${r.cod}', '${r.sigla}')" title="Ver usuarios conectados">👥 Ver (${r.users})</button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;

        container.innerHTML = html;
        return;
      }

      // -----------------------------------------------------------------------
      // VISTA B: ZONA ESPECÍFICA (I, II, III, IV, V, EXTRANJ, OTRAS)
      // -----------------------------------------------------------------------
      const z = zones.find(item => item.id === selectedOperationalZoneId) || zones[0];
      if (!z) {
        container.innerHTML = '<div style="color:var(--text-muted); padding:20px;">No se encontró información de la zona seleccionada.</div>';
        return;
      }

      const totalVal = z.total_connections || 0;
      const allReps = z.reparticiones || [];
      const topReps = allReps.slice(0, 8);

      // Filtered reparticiones
      const q = reparticionSearchTerm.trim().toLowerCase();
      const filteredReps = q 
        ? allReps.filter(r => r.sigla.toLowerCase().includes(q) || r.desc.toLowerCase().includes(q) || String(r.cod).includes(q))
        : allReps;

      let html = `
        <!-- Header de la Zona -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid var(--card-border); padding-bottom:14px; flex-wrap:wrap; gap:10px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="badge-pill" style="background:${z.color}20; color:${z.color}; border:1px solid ${z.color}50; font-size:12px; font-weight:800;">${z.sigla}</span>
              <h3 style="margin:0; font-size:17px; font-weight:800; color:#fff;">${z.name}</h3>
              <button class="btn btn-sm btn-outline" style="font-size:10px; padding:2px 7px; margin-left:6px;" onclick="selectOperationalZone('all')">🇨🇱 Ver Todo el País</button>
            </div>
            <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
              📍 Sede Principal: <strong style="color:#f8fafc;">${z.sede}</strong>
            </div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">
              🛡️ Jurisdicción: ${z.jurisdiccion}
            </div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:26px; font-weight:900; color:${z.color};">${z.unique_users || 0} <span style="font-size:13px; font-weight:normal; color:#cbd5e1;">Personas</span></div>
            <div style="font-size:11px; color:var(--text-muted);">${totalVal} Sesiones SSO Activas (${z.percentage}% del total nacional)</div>
          </div>
        </div>

        <!-- Bases Principales -->
        <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
          <span style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Bases Clave:</span>
          ${(z.bases || []).map(b => `<span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:6px; font-size:11px; color:#e2e8f0;">${b}</span>`).join('')}
        </div>

        <!-- Top Reparticiones Ranking -->
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:12px; font-weight:800; color:#fff; text-transform:uppercase; letter-spacing:0.5px;">🏆 Reparticiones Activas en esta Zona (${allReps.length})</span>
            <span style="font-size:11px; color:var(--text-muted);">Personas y sesiones concurrentes verificadas</span>
          </div>

          ${allReps.length === 0 ? `
            <div style="background:rgba(15,23,42,0.5); border:1px dashed #334155; border-radius:10px; padding:20px; text-align:center; color:var(--text-muted); font-size:12px;">
              ℹ️ No se registran personas conectadas en ${z.sigla} para el entorno <strong>${operationalMapData.env_name || ''}</strong>.
            </div>
          ` : `
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:10px;">
              ${topReps.map((r, idx) => `
                <div class="zone-rank-item" style="background:rgba(15,23,42,0.6); padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.05); cursor:pointer;" onclick="openReparticionUsersModal('${r.cod}', '${r.sigla}')" title="Clic para ver personas conectadas">
                  <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px;">
                    <div>
                      <span style="font-weight:800; color:${z.color}; text-decoration:underline;">#${idx + 1} ${r.sigla}</span>
                      <span style="color:#64748b; font-size:10px; margin-left:4px;">(Cod: ${r.cod})</span>
                    </div>
                    <span style="font-weight:700; color:#fff;">${r.users} personas <span style="font-size:10px; color:var(--text-muted);">(${r.pct}%)</span></span>
                  </div>
                  <div class="zone-rank-bar-bg" style="margin-top:2px;">
                    <div class="zone-rank-bar-fill" style="width:${Math.min(100, Math.max(6, r.pct))}%; background:linear-gradient(90deg, ${z.color}80, ${z.color});"></div>
                  </div>
                  <div style="display:flex; justify-content:space-between; font-size:10px; color:var(--text-muted); margin-top:2px;">
                    <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:180px;" title="${escapeHtml(r.desc)}">${r.desc}</span>
                    <span style="color:#38bdf8;">⚡ ${r.connections} sesión(es)</span>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>

        <!-- Catálogo Completo de Reparticiones Activas -->
        ${allReps.length > 0 ? `
          <div style="display:flex; flex-direction:column; gap:10px; margin-top:6px; flex:1;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:12px; font-weight:800; color:#fff; text-transform:uppercase; letter-spacing:0.5px;">📋 Detalle de Conexiones por Repartición (${allReps.length})</span>
                <span class="badge-pill badge-clean" style="font-size:10px;">${filteredReps.length} visibles</span>
              </div>
              <input type="text" class="search-input" placeholder="🔍 Filtrar por sigla o nombre..." 
                     value="${escapeHtml(reparticionSearchTerm)}" 
                     oninput="onSearchZoneReparticiones(this.value)" 
                     style="max-width:260px; font-size:11px; padding:6px 10px;">
            </div>

            <div style="max-height:360px; overflow-y:auto; border:1px solid var(--card-border); border-radius:10px;">
              <table class="reparticion-table">
                <thead>
                  <tr>
                    <th style="width:65px;">Código</th>
                    <th style="width:120px;">Sigla</th>
                    <th>Denominación Oficial</th>
                    <th style="width:85px; text-align:right;">Personas</th>
                    <th style="width:85px; text-align:right;">Sesiones</th>
                    <th style="width:70px; text-align:right;">% Zona</th>
                    <th style="width:85px; text-align:center;">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  ${filteredReps.length === 0 ? `
                    <tr>
                      <td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">
                        No se encontraron reparticiones con el término "${reparticionSearchTerm}".
                      </td>
                    </tr>
                  ` : filteredReps.map(r => `
                    <tr>
                      <td style="font-family:monospace; color:#64748b;">${r.cod}</td>
                      <td>
                        <strong style="color:${z.color}; cursor:pointer; text-decoration:underline;" onclick="openReparticionUsersModal('${r.cod}', '${r.sigla}')" title="Ver usuarios conectados en ${r.sigla}">${r.sigla}</strong>
                      </td>
                      <td style="color:#cbd5e1; font-size:11px;">${r.desc}</td>
                      <td style="text-align:right; font-weight:800; font-family:monospace; color:#38bdf8;">${r.users}</td>
                      <td style="text-align:right; color:#94a3b8; font-size:11px;">${r.connections}</td>
                      <td style="text-align:right; color:var(--text-muted); font-size:10px;">${r.pct}%</td>
                      <td style="text-align:center;">
                        <button class="btn btn-sm btn-outline" style="padding:2px 7px; font-size:10px; border-color:rgba(56,189,248,0.4); color:#38bdf8;" onclick="openReparticionUsersModal('${r.cod}', '${r.sigla}')" title="Ver usuarios conectados">👥 Ver (${r.users})</button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}
      `;

      container.innerHTML = html;
    }

    function onSearchZoneReparticiones(term) {
      reparticionSearchTerm = term;
      renderOperationalZoneDetail();
    }

    // -------------------------------------------------------------------------
    // Modal de Usuarios Conectados en Repartición (SSO)
    // -------------------------------------------------------------------------
    function openReparticionUsersModal(codRep, siglaRep) {
      if (!operationalMapData) return;
      
      let rep = (operationalMapData.all_active_reparticiones || []).find(r => String(r.cod) === String(codRep) || r.sigla === siglaRep);
      if (!rep) {
        for (const z of (operationalMapData.zones || [])) {
          const found = (z.reparticiones || []).find(r => String(r.cod) === String(codRep) || r.sigla === siglaRep);
          if (found) {
            rep = { ...found, zona_sigla: z.sigla, zona_color: z.color, zona_name: z.name };
            break;
          }
        }
      }

      const modal = document.getElementById('reparticionUsersModal');
      if (!modal) return;

      document.getElementById('repUsersModalSigla').innerText = siglaRep || (rep ? rep.sigla : 'REPARTICIÓN');
      
      const zoneBadge = document.getElementById('repUsersModalZoneBadge');
      if (zoneBadge) {
        zoneBadge.innerText = rep ? (rep.zona_sigla || 'ZONA') : 'ZONA';
        zoneBadge.style.color = rep ? rep.zona_color : '#38bdf8';
        zoneBadge.style.borderColor = rep ? rep.zona_color + '60' : '#38bdf8';
        zoneBadge.style.background = rep ? rep.zona_color + '20' : 'rgba(56,189,248,0.2)';
      }

      const countBadge = document.getElementById('repUsersModalCountBadge');
      if (countBadge) {
        countBadge.innerText = rep ? `${rep.users || 0} Persona(s) • ${rep.connections || 0} Sesión(es)` : '0 Personas';
      }

      const descEl = document.getElementById('repUsersModalDesc');
      if (descEl) {
        descEl.innerText = rep ? `${rep.desc || ''} (Código Repartición: ${rep.cod})` : '';
      }

      const metaEl = document.getElementById('repUsersModalMeta');
      if (metaEl) {
        metaEl.innerText = rep ? `Jurisdicción: ${rep.zona_name || rep.zona_sigla || 'Nacional'}` : '';
      }

      const envEl = document.getElementById('repUsersModalEnv');
      if (envEl) {
        envEl.innerText = `Entorno: ${(operationalMapData.env_name || operationalMapData.env || '').toUpperCase()}`;
      }

      const users = (rep && rep.active_users) ? rep.active_users : [];
      window._currentRepUsersList = users;
      window._currentRepSigla = siglaRep;

      const content = document.getElementById('repUsersModalContent');
      if (content) {
        if (users.length === 0) {
          content.innerHTML = `
            <div style="text-align:center; padding:35px 20px; color:var(--text-muted);">
              <div style="font-size:28px; margin-bottom:8px;">ℹ️</div>
              <div style="font-weight:700; color:#cbd5e1; font-size:13px;">No se registran personas conectadas en este momento</div>
              <div style="font-size:11px; margin-top:4px;">No hay sesiones SSO activas en Keycloak para ${siglaRep}.</div>
            </div>
          `;
        } else {
          content.innerHTML = `
            <table class="reparticion-table" style="width:100%; border-collapse:collapse;">
              <thead>
                <tr>
                  <th style="width:36px; text-align:center;">#</th>
                  <th style="width:130px;">Usuario / Login</th>
                  <th>Nombre y Apellidos</th>
                  <th>Correo Institucional</th>
                  <th style="width:100px; text-align:center;">Sesiones</th>
                  <th style="width:110px;">IP Conexión</th>
                  <th style="width:110px;">Inicio / Actividad</th>
                  <th style="width:75px; text-align:center;">Estado</th>
                  <th style="width:90px; text-align:center;">Seguimiento</th>
                </tr>
              </thead>
              <tbody>
                ${users.map((u, i) => {
                  const ts = u.last_access || u.start;
                  const startDate = ts ? new Date(ts).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-';
                  const sesBadge = (u.sessions_count && u.sessions_count > 1) 
                    ? `<span style="background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid rgba(56,189,248,0.4); font-weight:700; border-radius:10px; padding:2px 8px; font-size:11px;" title="${u.sessions_count} sesiones abiertas concurrentemente">${u.sessions_count} sesiones</span>`
                    : `<span style="background:rgba(255,255,255,0.06); color:#94a3b8; border-radius:10px; padding:2px 8px; font-size:11px;">1 sesión</span>`;
                  const adminBadge = u.is_admin 
                    ? `<span style="background:rgba(245,158,11,0.22); color:#fbbf24; border:1px solid #f59e0b; font-weight:800; border-radius:6px; padding:1px 6px; font-size:10px; margin-left:6px; display:inline-flex; align-items:center; gap:3px;" title="Usuario Administrador SISPER">👑 ADMIN</span>` 
                    : '';
                  const rowStyle = u.is_admin 
                    ? 'border-bottom:1px solid rgba(245,158,11,0.2); background:rgba(245,158,11,0.05);' 
                    : 'border-bottom:1px solid rgba(255,255,255,0.04);';
                  const safeName = (u.full_name || u.username).replace(/'/g, "\'");
                  return `
                    <tr style="${rowStyle}">
                      <td style="text-align:center; color:#64748b; font-size:11px;">${i + 1}</td>
                      <td>
                        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px;">
                          <span style="font-family:ui-monospace, monospace; font-weight:700; color:${u.is_admin ? '#fbbf24' : '#38bdf8'}; font-size:12px;">${u.username}</span>
                          ${adminBadge}
                        </div>
                      </td>
                      <td style="font-weight:600; color:#f8fafc; font-size:12px;">
                        ${u.full_name && u.full_name !== u.username ? u.full_name : '<span style="color:var(--text-muted); font-style:italic;">No Registrado</span>'}
                      </td>
                      <td style="color:#94a3b8; font-size:11px;">
                        ${u.email ? `<a href="mailto:${u.email}" style="color:#94a3b8; text-decoration:none;">${u.email}</a>` : '<span style="color:#64748b;">-</span>'}
                      </td>
                      <td style="text-align:center;">
                        ${sesBadge}
                      </td>
                      <td style="font-family:ui-monospace, monospace; color:#cbd5e1; font-size:11px;">
                        ${u.ip || '127.0.0.1'}
                      </td>
                      <td style="color:var(--text-muted); font-size:11px;">
                        ${startDate}
                      </td>
                      <td style="text-align:center;">
                        <span class="status-badge online" style="font-size:10px; padding:2px 6px;"><span class="dot"></span> Activo</span>
                      </td>
                      <td style="text-align:center;">
                        <button class="btn btn-sm btn-hero" onclick="trackUserFromMap('${u.username}', '${safeName}', ${Boolean(u.is_admin)}, '${u.ip || '-'}')" style="padding:2px 8px; font-size:10px; gap:4px; white-space:nowrap;" title="Ver en vivo qué está haciendo esta persona">
                          <span>⚡</span> En Vivo
                        </button>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          `;
        }
      }

      modal.style.display = 'flex';
    }

    function closeReparticionUsersModal() {
      const modal = document.getElementById('reparticionUsersModal');
      if (modal) modal.style.display = 'none';
    }

    function copyReparticionUsersList() {
      const users = window._currentRepUsersList || [];
      const sigla = window._currentRepSigla || 'Reparticion';
      if (users.length === 0) {
        showToast("No hay personas para copiar.");
        return;
      }
      const totalSessions = users.reduce((acc, u) => acc + (u.sessions_count || 1), 0);
      let text = `Personas Conectadas en ${sigla} (${users.length} personas • ${totalSessions} sesiones):
`;
      users.forEach((u, i) => {
        const sesText = (u.sessions_count && u.sessions_count > 1) ? `${u.sessions_count} sesiones` : '1 sesión';
        const admText = u.is_admin ? ' [👑 ADMIN]' : '';
        text += `${i + 1}. ${u.username}${admText} | ${u.full_name || '-'} | ${u.email || '-'} | ${sesText} | IP: ${u.ip || '-'}
`;
      });
      navigator.clipboard.writeText(text);
      showToast("Lista de personas copiada al portapapeles.");
    }

    function trackUserFromMap(username, fullName, isAdmin, ip) {
      closeReparticionUsersModal();
      switchTab('activity');
      connectToUser(username, username, fullName, isAdmin, ip);
    }

    // =========================================================================
    // AUDITORÍA DE ACTIVIDAD EN VIVO & TRAZABILIDAD (SISPER BITÁCORA)
    // =========================================================================
    let liveActivityData = null;
    let liveActivityEnv = 'develop';
    let liveActivityModuleFilter = 'all';
    let liveActivityMethodFilter = 'all';
    let liveActivityAutoInterval = null;
    let currentViewingTransaction = null;
    let liveActivityViewMode = 'users'; // 'users' (agrupado) | 'global' (tabla completa) | 'connected' (seguimiento activo)
    let connectedTrackingUser = null;   // { user_key, run, name, is_admin, ip, reparticion } o null
    let trackingFormat = 'timeline';    // 'timeline' | 'table'
    let trackingCountdownTimer = null;
    let trackingCountdownVal = 4;
    let previousActionIds = new Set();

    function switchActivityEnv(env) {
      liveActivityEnv = env;
      ['Dev', 'Test', 'Main'].forEach(e => {
        const btn = document.getElementById('btnActEnv' + e);
        if (btn) {
          btn.classList.remove('active');
          btn.style.background = 'transparent';
          btn.style.color = '#94a3b8';
        }
      });
      const activeBtnId = env === 'develop' ? 'btnActEnvDev' : (env === 'test' ? 'btnActEnvTest' : 'btnActEnvMain');
      const activeBtn = document.getElementById(activeBtnId);
      if (activeBtn) {
        activeBtn.classList.add('active');
        const color = env === 'develop' ? '#eab308' : (env === 'test' ? '#3b82f6' : '#10b981');
        const textColor = env === 'develop' ? '#000' : '#fff';
        activeBtn.style.background = color;
        activeBtn.style.color = textColor;
      }
      fetchLiveActivity(true);
    }

    function switchActivityViewMode(mode) {
      if (connectedTrackingUser && mode !== 'connected') {
        disconnectUserLiveTracking(false);
      }
      liveActivityViewMode = mode;
      
      const btnUsers = document.getElementById('btnActViewUsers');
      const btnGlobal = document.getElementById('btnActViewGlobal');
      const fmtSwitch = document.getElementById('trackingFormatSwitch');

      if (btnUsers && btnGlobal) {
        if (mode === 'users') {
          btnUsers.classList.add('active');
          btnUsers.style.background = '#38bdf8';
          btnUsers.style.color = '#0f172a';
          btnGlobal.classList.remove('active');
          btnGlobal.style.background = 'transparent';
          btnGlobal.style.color = '#94a3b8';
          if (fmtSwitch) fmtSwitch.style.display = 'none';
        } else if (mode === 'global') {
          btnGlobal.classList.add('active');
          btnGlobal.style.background = '#38bdf8';
          btnGlobal.style.color = '#0f172a';
          btnUsers.classList.remove('active');
          btnUsers.style.background = 'transparent';
          btnUsers.style.color = '#94a3b8';
          if (fmtSwitch) fmtSwitch.style.display = 'none';
        } else {
          // Connected tracking mode
          btnUsers.classList.remove('active');
          btnUsers.style.background = 'transparent';
          btnUsers.style.color = '#94a3b8';
          btnGlobal.classList.remove('active');
          btnGlobal.style.background = 'transparent';
          btnGlobal.style.color = '#94a3b8';
          if (fmtSwitch) fmtSwitch.style.display = 'flex';
        }
      }
      renderActivityViews();
    }

    function switchTrackingFormat(fmt) {
      trackingFormat = fmt;
      const btnTl = document.getElementById('btnFormatTimeline');
      const btnTb = document.getElementById('btnFormatTable');
      if (btnTl && btnTb) {
        if (fmt === 'timeline') {
          btnTl.classList.add('active');
          btnTl.style.background = '#0284c7';
          btnTl.style.color = '#fff';
          btnTb.classList.remove('active');
          btnTb.style.background = 'transparent';
          btnTb.style.color = '#94a3b8';
        } else {
          btnTb.classList.add('active');
          btnTb.style.background = '#0284c7';
          btnTb.style.color = '#fff';
          btnTl.classList.remove('active');
          btnTl.style.background = 'transparent';
          btnTl.style.color = '#94a3b8';
        }
      }
      renderActivityViews();
    }

    function connectToUser(userKey, run, name, isAdmin, ip, repSigla) {
      connectedTrackingUser = {
        user_key: userKey,
        run: run || userKey,
        name: name || userKey,
        is_admin: Boolean(isAdmin),
        ip: ip || '-',
        reparticion: repSigla || '-'
      };
      previousActionIds.clear();

      const banner = document.getElementById('activityConnectedUserBanner');
      if (banner) {
        banner.style.display = 'flex';
        document.getElementById('connectedUserName').innerText = connectedTrackingUser.name;
        document.getElementById('connectedUserRun').innerText = connectedTrackingUser.run;
        document.getElementById('connectedUserIp').innerText = connectedTrackingUser.ip;
        document.getElementById('connectedUserCount').innerText = '...';
        document.getElementById('connectedUserLastAction').innerText = 'Consultando...';
        document.getElementById('connectedUserSessionStatusText').innerText = 'Verificando SSO...';

        const repEl = document.getElementById('connectedUserRep');
        if (repEl) repEl.innerText = connectedTrackingUser.reparticion || '-';
        
        const admBadge = document.getElementById('connectedUserAdminBadge');
        if (admBadge) admBadge.style.display = connectedTrackingUser.is_admin ? 'inline-block' : 'none';

        const offAlert = document.getElementById('connectedUserOfflineAlert');
        if (offAlert) offAlert.style.display = 'none';

        const avatar = document.getElementById('connectedUserAvatar');
        if (avatar) {
          if (connectedTrackingUser.is_admin) {
            avatar.style.background = 'linear-gradient(135deg,#f59e0b,#fbbf24)';
            avatar.style.border = '1px solid #fbbf24';
            avatar.style.boxShadow = '0 0 15px rgba(245,158,11,0.5)';
            avatar.innerText = '👑';
          } else {
            avatar.style.background = 'linear-gradient(135deg,#10b981,#34d399)';
            avatar.style.border = 'none';
            avatar.style.boxShadow = '0 0 12px rgba(16,185,129,0.4)';
            avatar.innerText = (connectedTrackingUser.name || 'U')[0].toUpperCase();
          }
        }
      }

      switchActivityViewMode('connected');
      fetchLiveActivity(true);
      startTrackingCountdown();
      showToast(`🟢 Rastreando en vivo a: ${connectedTrackingUser.name}`);
    }

    function disconnectUserLiveTracking(refetch = true) {
      connectedTrackingUser = null;
      if (trackingCountdownTimer) {
        clearInterval(trackingCountdownTimer);
        trackingCountdownTimer = null;
      }

      const banner = document.getElementById('activityConnectedUserBanner');
      if (banner) banner.style.display = 'none';

      const fmtSwitch = document.getElementById('trackingFormatSwitch');
      if (fmtSwitch) fmtSwitch.style.display = 'none';

      switchActivityViewMode('users');
      if (refetch) {
        fetchLiveActivity(true);
      }
      showToast('Desconectado del seguimiento individual.');
    }

    function startTrackingCountdown() {
      if (trackingCountdownTimer) clearInterval(trackingCountdownTimer);
      trackingCountdownVal = 4;
      updateCountdownDisplay();

      trackingCountdownTimer = setInterval(() => {
        if (!connectedTrackingUser) {
          clearInterval(trackingCountdownTimer);
          trackingCountdownTimer = null;
          return;
        }

        const activeTab = document.querySelector('.tab-link.active');
        if (!activeTab || activeTab.getAttribute('data-tab') !== 'activity') {
          return;
        }

        trackingCountdownVal--;
        if (trackingCountdownVal <= 0) {
          trackingCountdownVal = 4;
          const cdEl = document.getElementById('connectedUserCountdown');
          if (cdEl) cdEl.innerText = '🔄 Comprobando...';
          fetchLiveActivity(false);
        } else {
          updateCountdownDisplay();
        }
      }, 1000);
    }

    function updateCountdownDisplay() {
      const cdEl = document.getElementById('connectedUserCountdown');
      if (cdEl) {
        cdEl.innerText = `Refresco en ${trackingCountdownVal}s...`;
      }
    }

    async function fetchLiveActivity(force = false) {
      const spinner = document.getElementById('activitySpinner');
      if (spinner && force) spinner.style.display = 'inline-block';

      const limit = document.getElementById('activityLimitSelect') ? document.getElementById('activityLimitSelect').value : 50;
      const search = document.getElementById('activitySearchInput') ? document.getElementById('activitySearchInput').value.trim() : '';

      try {
        let url = `/api/activity/feed?env=${encodeURIComponent(liveActivityEnv)}&limit=${limit}&modulo=${encodeURIComponent(liveActivityModuleFilter)}&metodo=${encodeURIComponent(liveActivityMethodFilter)}&search=${encodeURIComponent(search)}`;
        if (connectedTrackingUser) {
          url += `&user=${encodeURIComponent(connectedTrackingUser.user_key || connectedTrackingUser.run)}&limit=150`;
        }

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        liveActivityData = data;

        // Si estamos siguiendo a un usuario específico, procesar su estado de sesión en Keycloak SSO
        if (connectedTrackingUser) {
          const cCount = document.getElementById('connectedUserCount');
          if (cCount) cCount.innerText = `${data.count || 0}`;

          const cLast = document.getElementById('connectedUserLastAction');
          if (cLast) {
            cLast.innerText = (data.items && data.items.length > 0) ? formatRelativeTime(data.items[0].fecha_ejecucion) : 'Sin acciones';
          }

          const banner = document.getElementById('activityConnectedUserBanner');
          const onBadge = document.getElementById('connectedUserOnlineBadge');
          const offAlert = document.getElementById('connectedUserOfflineAlert');
          const offTime = document.getElementById('connectedUserOfflineTime');
          const sessTxt = document.getElementById('connectedUserSessionStatusText');
          const rDot = document.getElementById('connectedUserRadarDot');

          if (data.user_session) {
            const sso = data.user_session;
            if (sso.is_online) {
              if (onBadge) {
                onBadge.innerHTML = `<span class="dot" style="background:#10b981; box-shadow:0 0 8px #10b981;"></span><span>🟢 EN LÍNEA (${sso.sessions_count || 1} ses.)</span>`;
                onBadge.style.color = '#34d399';
                onBadge.style.borderColor = 'rgba(16,185,129,0.4)';
                onBadge.style.background = 'rgba(16,185,129,0.2)';
              }
              if (sessTxt) sessTxt.innerHTML = `<span style="color:#34d399;">🟢 Activa (${sso.sessions_count || 1})</span>`;
              if (offAlert) offAlert.style.display = 'none';
              if (banner) {
                banner.style.borderColor = '#10b981';
                banner.style.boxShadow = '0 8px 30px rgba(0,0,0,0.4), 0 0 25px rgba(16,185,129,0.15)';
              }
              if (rDot) {
                rDot.style.background = '#10b981';
                rDot.style.boxShadow = '0 0 8px #10b981';
              }
              if (sso.reparticion_sigla) {
                const repEl = document.getElementById('connectedUserRep');
                if (repEl) repEl.innerText = sso.reparticion_sigla + (sso.zona_sigla ? ' • ' + sso.zona_sigla : '');
              }
              if (sso.ip && sso.ip !== '-') {
                const ipEl = document.getElementById('connectedUserIp');
                if (ipEl) ipEl.innerText = sso.ip;
              }
            } else {
              // Usuario desconectado de Keycloak
              if (onBadge) {
                onBadge.innerHTML = `<span class="dot" style="background:#ef4444; box-shadow:0 0 8px #ef4444;"></span><span>🔴 DESCONECTADO (Sesión Cerrada)</span>`;
                onBadge.style.color = '#f87171';
                onBadge.style.borderColor = 'rgba(239,68,68,0.5)';
                onBadge.style.background = 'rgba(239,68,68,0.2)';
              }
              if (sessTxt) sessTxt.innerHTML = `<span style="color:#f87171;">🔴 Desconectado</span>`;
              if (offAlert) offAlert.style.display = 'flex';
              if (offTime) offTime.innerText = `Comprobado: ${sso.checked_at || new Date().toLocaleTimeString()}`;
              if (banner) {
                banner.style.borderColor = '#ef4444';
                banner.style.boxShadow = '0 8px 30px rgba(0,0,0,0.4), 0 0 25px rgba(239,68,68,0.2)';
              }
              if (rDot) {
                rDot.style.background = '#ef4444';
                rDot.style.boxShadow = '0 0 8px #ef4444';
              }
            }
          }

          // Actualización de Telemetría Frontend (Opción 1: Pantalla, Pestaña, Interacción viva)
          const tele = data.live_telemetry;
          const teleCard = document.getElementById('connectedUserFrontendTelemetry');
          const teleBadge = document.getElementById('connectedUserTeleActiveBadge');
          const rName = document.getElementById('telemetryRouteName');
          const rHash = document.getElementById('telemetryRouteHash');
          const tVis = document.getElementById('telemetryTabVisibility');
          const tState = document.getElementById('telemetryInteractionState');
          const tField = document.getElementById('telemetryFieldTarget');
          const tTime = document.getElementById('telemetryTimeOnView');
          const tRes = document.getElementById('telemetryResolution');

          if (tele) {
            if (teleBadge) {
              teleBadge.innerText = '🟢 Telemetría Activa (En Vivo)';
              teleBadge.style.color = '#34d399';
              teleBadge.style.borderColor = 'rgba(16,185,129,0.4)';
              teleBadge.style.background = 'rgba(16,185,129,0.15)';
            }
            if (rName) rName.innerText = tele.route_name || 'Inicio / Resumen';
            if (rHash) rHash.innerText = tele.full_hash || tele.route || '#/';
            
            if (tVis) {
              if (tele.tab_visibility === 'visible') {
                tVis.innerHTML = `<span style="color:#34d399; font-weight:800;">🟢 Primer plano (Activa)</span>`;
              } else if (tele.tab_visibility === 'focused_out') {
                tVis.innerHTML = `<span style="color:#38bdf8; font-weight:800;">🔵 Visible (Sin foco)</span>`;
              } else {
                tVis.innerHTML = `<span style="color:#f59e0b; font-weight:800;">🟡 Segundo plano (Minimizada)</span>`;
              }
            }

            if (tState) {
              if (tele.interaction === 'typing') {
                tState.innerHTML = `<span style="color:#ec4899; font-weight:800;">✍️ Escribiendo en Formulario</span>`;
                if (tField) tField.innerText = tele.current_field ? `Campo: ${tele.current_field}` : 'Editando datos';
              } else if (tele.interaction === 'idle') {
                tState.innerHTML = `<span style="color:#94a3b8; font-weight:800;">💤 Inactivo (+45s)</span>`;
                if (tField) tField.innerText = 'Sin movimiento reciente';
              } else {
                tState.innerHTML = `<span style="color:#38bdf8; font-weight:800;">👀 Navegando / Leyendo</span>`;
                if (tField) tField.innerText = 'Interactuando con pantalla';
              }
            }

            if (tTime) {
              const sec = tele.seconds_on_view || 0;
              const min = Math.floor(sec / 60);
              const remSec = sec % 60;
              tTime.innerText = min > 0 ? `${min}m ${remSec}s en esta pantalla` : `${sec} seg en esta pantalla`;
            }

            if (tRes) tRes.innerText = `Ventana: ${tele.window_size || '1920x1080'}`;
          } else {
            if (teleBadge) {
              teleBadge.innerText = '⏳ Esperando latido...';
              teleBadge.style.color = '#94a3b8';
              teleBadge.style.borderColor = 'rgba(148,163,184,0.3)';
              teleBadge.style.background = 'rgba(148,163,184,0.1)';
            }
            if (rName) rName.innerText = 'A la espera del navegador';
            if (rHash) rHash.innerText = 'Sin telemetría activa aún';
            if (tVis) tVis.innerHTML = `<span style="color:#94a3b8;">-</span>`;
            if (tState) tState.innerHTML = `<span style="color:#94a3b8;">-</span>`;
            if (tField) tField.innerText = '-';
            if (tTime) tTime.innerText = '-';
          }

          // Detección de nuevos movimientos en vivo
          if (previousActionIds.size > 0 && data.items && data.items.length > 0) {
            const newActions = data.items.filter(it => !previousActionIds.has(it.id));
            if (newActions.length > 0) {
              showToast(`⚡ +${newActions.length} nuevo(s) movimiento(s) de ${connectedTrackingUser.name}`);
            }
          }
          if (data.items) {
            previousActionIds = new Set(data.items.map(it => it.id));
          }
        }

        renderLiveActivityKpis();
        renderActivityViews();

        const upd = document.getElementById('activityLastUpdated');
        if (upd) {
          const dbInfo = (data.db_host) ? ` • BD: ${data.db_host}:${data.db_port || 5432}` : '';
          const gwInfo = (data.env_ip) ? ` • Ingress: ${data.env_ip}` : '';
          upd.innerText = `Actualizado: ${data.timestamp || new Date().toLocaleTimeString()} (${data.latency_ms || 0}ms)${gwInfo}${dbInfo}`;
        }
      } catch (err) {
        console.error('Error fetching live activity:', err);
        // El pie debe decir que la consulta falló, no quedarse en "Actualizado: -"
        // como si el resultado vacío fuese un dato.
        const upd = document.getElementById('activityLastUpdated');
        if (upd) upd.innerText = `No se pudo consultar: ${err.message || 'error desconocido'}`;
        showToast('Error cargando actividad en vivo: ' + err.message);
      } finally {
        if (spinner) spinner.style.display = 'none';
      }
    }

    function renderActivityViews() {
      const usersView = document.getElementById('activityUsersView');
      const timelineView = document.getElementById('activityTimelineView');
      const trackingTlView = document.getElementById('activityTrackingTimelineView');
      const banner = document.getElementById('activityConnectedUserBanner');
      const fmtSwitch = document.getElementById('trackingFormatSwitch');

      if (connectedTrackingUser) {
        if (banner) banner.style.display = 'flex';
        if (fmtSwitch) fmtSwitch.style.display = 'flex';
        if (usersView) usersView.style.display = 'none';

        if (trackingFormat === 'timeline') {
          if (trackingTlView) trackingTlView.style.display = 'block';
          if (timelineView) timelineView.style.display = 'none';
          renderTrackingTimeline();
        } else {
          if (trackingTlView) trackingTlView.style.display = 'none';
          if (timelineView) timelineView.style.display = 'block';
          renderLiveActivityTable();
        }
      } else {
        if (banner) banner.style.display = 'none';
        if (fmtSwitch) fmtSwitch.style.display = 'none';
        if (trackingTlView) trackingTlView.style.display = 'none';

        if (liveActivityViewMode === 'users') {
          if (usersView) usersView.style.display = 'block';
          if (timelineView) timelineView.style.display = 'none';
          renderActivityUsersCards();
        } else {
          if (usersView) usersView.style.display = 'none';
          if (timelineView) timelineView.style.display = 'block';
          renderLiveActivityTable();
        }
      }
    }

    function renderTrackingTimeline() {
      const container = document.getElementById('trackingTimelineFlow');
      if (!container || !liveActivityData) return;

      const items = liveActivityData.items || [];
      if (items.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding:50px 20px; color:var(--text-muted); font-size:13px; background:rgba(15,23,42,0.4); border-radius:12px; border:1px dashed var(--card-border);">
            <div style="font-size:32px; margin-bottom:10px;">⏳</div>
            <div style="font-weight:700; color:#cbd5e1; margin-bottom:4px;">A la espera de movimientos en el sistema</div>
            <div style="font-size:11px; color:var(--text-muted);">Los eventos aparecerán automáticamente en esta línea temporal tan pronto la persona ejecute acciones en los microservicios.</div>
          </div>
        `;
        return;
      }

      container.innerHTML = items.map((it, idx) => {
        const modStyle = getModuleBadgeStyle(it.modulo);
        const methodBadge = getMethodBadge(it.metodo);
        const statusBadge = getHttpStatusBadge(it.response_code);
        const relTime = formatRelativeTime(it.fecha_ejecucion);
        const timeOnly = it.fecha_ejecucion ? it.fecha_ejecucion.split('T')[1]?.split('.')[0] || '' : '';
        const urlDisplay = (it.url_endpoint || '').replace(/https?:\/\/[^\/]+/, '');
        const hasPayload = (it.transaccion_preview && it.transaccion_preview.trim().length > 0 && it.transaccion_preview !== '{}');

        return `
          <div class="tracking-event-card" style="position:relative; background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:14px 16px; transition:all 0.2s; box-shadow:0 4px 16px rgba(0,0,0,0.2);">
            <!-- Nodo Conector en la línea temporal -->
            <div style="position:absolute; left:-27px; top:16px; width:12px; height:12px; border-radius:50%; background:#38bdf8; box-shadow:0 0 10px #38bdf8; border:2px solid #0f172a;"></div>

            <!-- Cabecera de la acción -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span class="badge-pill" style="font-size:10px; padding:2px 8px; background:${modStyle.bg}; border-color:${modStyle.border}; color:${modStyle.color}; font-weight:800; display:inline-flex; align-items:center; gap:4px;">
                  <span>${modStyle.icon}</span>
                  <span>${it.modulo}</span>
                </span>
                ${methodBadge}
                ${statusBadge}
              </div>
              <div style="text-align:right;">
                <div style="font-weight:800; color:#f8fafc; font-size:12px; font-family:monospace;">${timeOnly}</div>
                <div style="font-size:10px; color:var(--text-muted);">${relTime}</div>
              </div>
            </div>

            <!-- Endpoint -->
            <div style="background:rgba(0,0,0,0.3); border-radius:6px; padding:8px 12px; font-family:ui-monospace, monospace; font-size:11.5px; color:#a5f3fc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border:1px solid rgba(255,255,255,0.04); margin-bottom:10px;" title="${escapeHtml(it.url_endpoint)}">
              ${urlDisplay || it.url_endpoint}
            </div>

            <!-- Footer con IP y Botones de Inspección -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; font-size:11px;">
              <div style="color:#94a3b8;">
                <span>IP Origen:</span> <strong style="font-family:monospace; color:#cbd5e1;">${it.ip_ejecutor || '-'}</strong>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                ${hasPayload ? `
                  <button class="btn btn-sm btn-outline" onclick="toggleInlinePayload('${it.id}')" style="padding:2px 8px; font-size:10.5px; border-color:rgba(56,189,248,0.4); color:#38bdf8;">
                    👁️ Carga Rápida
                  </button>
                ` : ''}
                <button class="btn btn-sm btn-hero" onclick="openTransactionDetailModal('${it.id}')" style="padding:2px 8px; font-size:10.5px;">
                  🔍 Ver Completo
                </button>
              </div>
            </div>

            <!-- Contenedor Desplegable de Payload Inline -->
            <div id="inlinePayload-${it.id}" style="display:none; margin-top:10px; padding:10px; background:#0b1120; border:1px solid rgba(56,189,248,0.25); border-radius:6px; font-family:ui-monospace, monospace; font-size:10.5px; color:#e2e8f0; max-height:220px; overflow-y:auto; white-space:pre-wrap; word-break:break-all;">
              ${escapeHtml(it.transaccion_preview || 'Sin carga disponible')}
            </div>
          </div>
        `;
      }).join('');
    }

    function toggleInlinePayload(id) {
      const el = document.getElementById('inlinePayload-' + id);
      if (el) {
        el.style.display = (el.style.display === 'none' || !el.style.display) ? 'block' : 'none';
      }
    }


    function renderActivityUsersCards() {
      const grid = document.getElementById('activityUsersGrid');
      const badge = document.getElementById('activityCountBadge');
      if (!grid || !liveActivityData) return;

      const users = liveActivityData.users || [];
      if (badge) badge.innerText = `${users.length} personas con movimientos`;

      if (users.length === 0) {
        grid.innerHTML = `
          <div style="grid-column:1/-1; text-align:center; padding:45px 20px; color:var(--text-muted); font-size:13px; background:rgba(15,23,42,0.4); border-radius:12px; border:1px dashed var(--card-border);">
            <div style="font-size:32px; margin-bottom:10px;">👥</div>
            <div style="font-weight:700; color:#cbd5e1; margin-bottom:4px;">No se encontraron personas con movimientos recientes</div>
            <div style="font-size:11px; color:var(--text-muted);">Prueba cambiando de entorno (DEVELOP, TEST, MAIN) o ajustando los filtros de módulo y búsqueda.</div>
          </div>
        `;
        return;
      }

      grid.innerHTML = users.map(u => {
        const isAdmin = Boolean(u.is_admin);
        const avatarBg = isAdmin ? 'linear-gradient(135deg,#f59e0b,#fbbf24)' : 'linear-gradient(135deg,#0284c7,#38bdf8)';
        const avatarBorder = isAdmin ? 'border:1px solid #fbbf24; box-shadow:0 0 10px rgba(245,158,11,0.4);' : '';
        const adminBadge = isAdmin ? '<span style="background:rgba(245,158,11,0.22); color:#fbbf24; border:1px solid #f59e0b; padding:1px 6px; border-radius:4px; font-size:9.5px; font-weight:800; letter-spacing:0.5px;">👑 ADMIN</span>' : '';
        const relTime = formatRelativeTime(u.last_action_time);
        const modStyle = getModuleBadgeStyle(u.last_modulo);
        const safeName = (u.nombre_completo || 'Desconocido').replace(/'/g, "\'");
        const cleanEndpoint = (u.last_endpoint || '').replace(/https?:\/\/[^\/]+/, '');

        return `
          <div class="panel-box" style="background:rgba(15,23,42,0.85); border:1px solid ${isAdmin ? 'rgba(245,158,11,0.35)' : 'rgba(255,255,255,0.08)'}; border-radius:12px; padding:16px; display:flex; flex-direction:column; justify-content:space-between; transition:all 0.2s; box-shadow:0 4px 14px rgba(0,0,0,0.25);" onmouseenter="this.style.borderColor='${isAdmin ? '#fbbf24' : '#38bdf8'}'; this.style.transform='translateY(-2px)';" onmouseleave="this.style.borderColor='${isAdmin ? 'rgba(245,158,11,0.35)' : 'rgba(255,255,255,0.08)'}'; this.style.transform='none';">
            <div>
              <!-- Header Persona -->
              <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:10px;">
                  <div style="width:38px; height:38px; border-radius:50%; background:${avatarBg}; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px; color:#fff; flex-shrink:0; ${avatarBorder}">
                    ${isAdmin ? '👑' : (u.nombre_completo || 'U')[0].toUpperCase()}
                  </div>
                  <div>
                    <div style="font-weight:700; color:#f8fafc; font-size:13px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                      <span>${u.nombre_completo || 'Desconocido'}</span>
                      ${adminBadge}
                    </div>
                    <div style="font-size:11px; color:#38bdf8; font-family:monospace; margin-top:2px;">
                      RUN: ${u.run_ejecutor || '-'}
                    </div>
                  </div>
                </div>
                <span class="badge-pill" style="font-size:10.5px; background:rgba(16,185,129,0.15); color:#34d399; border-color:rgba(16,185,129,0.3); font-weight:700; white-space:nowrap;">
                  ⚡ ${u.total_actions} acciones
                </span>
              </div>

              <!-- Bloque Técnico de Último Movimiento -->
              <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px 12px; margin-bottom:14px; font-size:11px; display:flex; flex-direction:column; gap:6px; border:1px solid rgba(255,255,255,0.04);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span style="color:var(--text-muted);">Último movimiento:</span>
                  <span style="color:#cbd5e1; font-weight:600;">${relTime}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
                  <span style="color:var(--text-muted);">Microservicio:</span>
                  <span class="badge-pill" style="font-size:9.5px; padding:2px 7px; background:${modStyle.bg}; border-color:${modStyle.border}; color:${modStyle.color}; font-weight:700;">
                    ${modStyle.icon} ${u.last_modulo || '-'}
                  </span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span style="color:var(--text-muted);">IP Origen:</span>
                  <span style="font-family:monospace; color:#94a3b8;">${u.ip_ejecutor || '-'}</span>
                </div>
                <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#a5f3fc; font-family:monospace; font-size:10px; margin-top:3px; background:rgba(0,0,0,0.25); padding:3px 6px; border-radius:4px;" title="${escapeHtml(u.last_endpoint)}">
                  ${u.last_metodo || 'POST'} ${cleanEndpoint || u.last_endpoint}
                </div>
              </div>
            </div>

            <!-- Botón Conectar y Ver en Vivo -->
            <button class="btn btn-sm btn-hero" onclick="connectToUser('${u.user_key}', '${u.run_ejecutor}', '${safeName}', ${isAdmin}, '${u.ip_ejecutor}')" style="width:100%; justify-content:center; padding:7px 12px; font-size:11.5px; gap:6px; font-weight:700;">
              <span>⚡</span>
              <span>Conectarme y Ver en Vivo</span>
            </button>
          </div>
        `;
      }).join('');
    }

    function toggleActivityAutoRefresh() {
      const chk = document.getElementById('activityAutoRefreshToggle');
      const dot = document.getElementById('activityLiveIndicator');
      if (chk && chk.checked) {
        if (dot) {
          dot.style.background = '#10b981';
          dot.style.boxShadow = '0 0 8px #10b981';
        }
        if (!liveActivityAutoInterval) {
          liveActivityAutoInterval = setInterval(() => {
            const activeTab = document.querySelector('.tab-link.active');
            if (activeTab && activeTab.getAttribute('data-tab') === 'activity') {
              fetchLiveActivity(false);
            }
          }, 15000);   // cada sondeo cuesta 1,75 s de consulta a Bitácora
        }
      } else {
        if (dot) {
          dot.style.background = '#64748b';
          dot.style.boxShadow = 'none';
        }
        if (liveActivityAutoInterval) {
          clearInterval(liveActivityAutoInterval);
          liveActivityAutoInterval = null;
        }
      }
    }

    function renderLiveActivityKpis() {
      const container = document.getElementById('activityKpiRow');
      if (!container || !liveActivityData) return;

      const d = liveActivityData;
      const itemsCount = d.count || 0;
      const uniqueUsers = d.unique_users_count || 0;
      const successRate = d.success_rate !== undefined ? d.success_rate : 100;
      const topModule = d.top_module || 'Ninguno';
      const errorCount = d.error_count || 0;

      container.innerHTML = `
        <div class="panel-box" style="flex:1 1 200px; min-width:180px; background:rgba(15,23,42,0.85); border-color:rgba(56,189,248,0.3);">
          <div class="panel-box-header">
            <span class="panel-box-title" style="color:#38bdf8; font-size:11.5px;">⚡ TRANSACCIONES RECIENTES</span>
          </div>
          <div style="font-size:24px; font-weight:800; color:#fff; margin-top:4px;">${itemsCount}</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">Mostradas en el feed actual</div>
        </div>

        <div class="panel-box" style="flex:1 1 200px; min-width:180px; background:rgba(15,23,42,0.85); border-color:rgba(16,185,129,0.3);">
          <div class="panel-box-header">
            <span class="panel-box-title" style="color:#10b981; font-size:11.5px;">👥 PERSONAS CON ACTIVIDAD</span>
          </div>
          <div style="font-size:24px; font-weight:800; color:#fff; margin-top:4px;">${uniqueUsers} <span style="font-size:13px; font-weight:500; color:var(--text-muted);">personas</span></div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">Ejecutando transacciones en feed</div>
        </div>

        <div class="panel-box" style="flex:1 1 200px; min-width:180px; background:rgba(15,23,42,0.85); border-color:${errorCount > 0 ? 'rgba(239,68,68,0.4)' : 'rgba(16,185,129,0.3)'};">
          <div class="panel-box-header">
            <span class="panel-box-title" style="color:${errorCount > 0 ? '#f87171' : '#34d399'}; font-size:11.5px;">🎯 TASA DE ÉXITO HTTP</span>
          </div>
          <div style="font-size:24px; font-weight:800; color:${errorCount > 0 ? '#fbbf24' : '#10b981'}; margin-top:4px;">${successRate}%</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${itemsCount - errorCount} exitosas • ${errorCount} errores</div>
        </div>

        <div class="panel-box" style="flex:1 1 200px; min-width:180px; background:rgba(15,23,42,0.85); border-color:rgba(168,85,247,0.3);">
          <div class="panel-box-header">
            <span class="panel-box-title" style="color:#c084fc; font-size:11.5px;">📦 MÓDULO CON MÁS ACTIVIDAD</span>
          </div>
          <div style="font-size:17px; font-weight:800; color:#fff; margin-top:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${topModule}">${topModule}</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Mayor concurrencia registrada</div>
        </div>
      `;
    }

    function getModuleBadgeStyle(mod) {
      const m = (mod || '').toUpperCase();
      if (m.includes('CONTRATO')) return { bg: 'rgba(2,132,199,0.2)', border: '#0284c7', color: '#38bdf8', icon: '📝' };
      if (m.includes('SESI')) return { bg: 'rgba(16,185,129,0.2)', border: '#10b981', color: '#34d399', icon: '🔐' };
      if (m.includes('IDENTIFIC')) return { bg: 'rgba(168,85,247,0.2)', border: '#a855f7', color: '#c084fc', icon: '🪪' };
      if (m.includes('USUARIO')) return { bg: 'rgba(245,158,11,0.2)', border: '#f59e0b', color: '#fbbf24', icon: '👤' };
      if (m.includes('SOLICITUD')) return { bg: 'rgba(236,72,153,0.2)', border: '#ec4899', color: '#f472b6', icon: '📩' };
      if (m.includes('CARRERA')) return { bg: 'rgba(99,102,241,0.2)', border: '#6366f1', color: '#818cf8', icon: '🎖️' };
      return { bg: 'rgba(148,163,184,0.15)', border: '#64748b', color: '#cbd5e1', icon: '📦' };
    }

    function getMethodBadge(metodo) {
      const m = (metodo || 'POST').toUpperCase();
      if (m === 'POST') return `<span style="font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; background:rgba(16,185,129,0.2); color:#34d399; border:1px solid #10b981;">POST</span>`;
      if (m === 'PUT') return `<span style="font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; background:rgba(245,158,11,0.2); color:#fbbf24; border:1px solid #f59e0b;">PUT</span>`;
      if (m === 'PATCH') return `<span style="font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; background:rgba(249,115,22,0.2); color:#fb923c; border:1px solid #f97316;">PATCH</span>`;
      if (m === 'DELETE') return `<span style="font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; background:rgba(239,68,68,0.2); color:#f87171; border:1px solid #ef4444;">DELETE</span>`;
      return `<span style="font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; background:rgba(148,163,184,0.2); color:#cbd5e1; border:1px solid #64748b;">${m}</span>`;
    }

    function getHttpStatusBadge(code) {
      const c = parseInt(code, 10) || 200;
      if (c >= 200 && c < 300) {
        return `<span class="badge-pill" style="font-size:10px; font-weight:700; background:rgba(16,185,129,0.15); color:#34d399; border-color:#10b981;">${c} OK</span>`;
      }
      if (c >= 300 && c < 400) {
        return `<span class="badge-pill" style="font-size:10px; font-weight:700; background:rgba(56,189,248,0.15); color:#38bdf8; border-color:#0284c7;">${c}</span>`;
      }
      if (c >= 400 && c < 500) {
        return `<span class="badge-pill" style="font-size:10px; font-weight:700; background:rgba(245,158,11,0.15); color:#fbbf24; border-color:#f59e0b;">${c} Warn</span>`;
      }
      return `<span class="badge-pill" style="font-size:10px; font-weight:700; background:rgba(239,68,68,0.2); color:#f87171; border-color:#ef4444;">${c} Err</span>`;
    }

    function formatRelativeTime(dateStr) {
      if (!dateStr) return '-';
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      const now = new Date();
      const diffSec = Math.floor((now - d) / 1000);
      if (diffSec < 15) return 'Hace un instante';
      if (diffSec < 60) return `Hace ${diffSec}s`;
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `Hace ${diffMin}m`;
      const diffHour = Math.floor(diffMin / 60);
      if (diffHour < 24) return `Hace ${diffHour}h`;
      return d.toLocaleDateString();
    }

    function renderLiveActivityTable() {
      const tbody = document.getElementById('activityTableBody');
      const badge = document.getElementById('activityCountBadge');
      if (!tbody || !liveActivityData) return;

      const items = liveActivityData.items || [];
      if (badge && !connectedTrackingUser) badge.innerText = `${items.length} registros`;

      if (items.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" style="text-align:center; padding:40px; color:var(--text-muted); font-size:13px;">
              No se encontraron transacciones registradas con los filtros seleccionados en <strong>${(liveActivityData.env || '').toUpperCase()}</strong>.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = items.map((it, idx) => {
        const modStyle = getModuleBadgeStyle(it.modulo);
        const methodBadge = getMethodBadge(it.metodo);
        const statusBadge = getHttpStatusBadge(it.response_code);
        const relTime = formatRelativeTime(it.fecha_ejecucion);
        const timeOnly = it.fecha_ejecucion ? it.fecha_ejecucion.split('T')[1]?.split('.')[0] || '' : '';
        const dateOnly = it.fecha_ejecucion ? it.fecha_ejecucion.split('T')[0] : '';
        const urlDisplay = (it.url_endpoint || '').replace(/https?:\/\/[^\/]+/, '');

        const isAdmin = Boolean(it.is_admin);
        const rowStyle = isAdmin ? 'transition:background 0.15s; border-bottom:1px solid rgba(255,255,255,0.04); background:rgba(245,158,11,0.04);' : 'transition:background 0.15s; border-bottom:1px solid rgba(255,255,255,0.04);';
        const avatarBg = isAdmin ? 'linear-gradient(135deg,#f59e0b,#fbbf24)' : 'linear-gradient(135deg,#0284c7,#38bdf8)';
        const avatarBorder = isAdmin ? 'border:1px solid #fbbf24; box-shadow:0 0 8px rgba(245,158,11,0.4);' : '';
        const adminBadge = isAdmin ? '<span style="background:rgba(245,158,11,0.2); color:#fbbf24; border:1px solid rgba(245,158,11,0.4); padding:1px 5px; border-radius:4px; font-size:9.5px; font-weight:800; letter-spacing:0.5px;">👑 ADMIN</span>' : '';

        return `
          <tr style="${rowStyle}">
            <td style="white-space:nowrap;">
              <div style="font-weight:700; color:#f8fafc; font-size:12px;">${timeOnly}</div>
              <div style="font-size:10px; color:var(--text-muted);">${relTime} • ${dateOnly}</div>
            </td>
            <td>
              <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:28px; height:28px; border-radius:50%; background:${avatarBg}; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:11px; color:#fff; flex-shrink:0; ${avatarBorder}">
                  ${isAdmin ? '👑' : (it.nombre_completo || 'U')[0].toUpperCase()}
                </div>
                <div>
                  <div style="font-weight:600; color:#f1f5f9; font-size:12px; display:flex; align-items:center; gap:6px;">
                    <span>${it.nombre_completo || 'Desconocido'}</span>
                    ${adminBadge}
                  </div>
                  <div style="display:flex; align-items:center; gap:6px; margin-top:2px;">
                    <span style="font-family:ui-monospace, monospace; font-size:10px; color:#38bdf8; font-weight:700; background:rgba(56,189,248,0.1); padding:1px 4px; border-radius:3px;">${it.run_ejecutor || '-'}</span>
                  </div>
                </div>
              </div>
            </td>
            <td>
              <span class="badge-pill" style="font-size:10px; padding:3px 8px; background:${modStyle.bg}; border-color:${modStyle.border}; color:${modStyle.color}; font-weight:700; display:inline-flex; align-items:center; gap:4px;">
                <span>${modStyle.icon}</span>
                <span>${it.modulo}</span>
              </span>
            </td>
            <td style="text-align:center;">
              ${methodBadge}
            </td>
            <td>
              <div style="font-family:ui-monospace, monospace; font-size:11px; color:#a5f3fc; max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(it.url_endpoint)}">
                ${urlDisplay || it.url_endpoint}
              </div>
            </td>
            <td style="text-align:center;">
              ${statusBadge}
            </td>
            <td style="font-family:ui-monospace, monospace; font-size:11px; color:#94a3b8;">
              ${it.ip_ejecutor || '-'}
            </td>
            <td style="text-align:center;">
              <button class="btn btn-sm btn-outline" onclick="openTransactionDetailModal('${it.id}')" title="Ver carga de datos transada" style="padding:3px 7px; font-size:10.5px;">
                🔍 Ver
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function filterActivityClientSide() {
      const q = document.getElementById('activitySearchInput').value.toLowerCase().trim();
      
      // Filtrar filas de tabla
      const rows = document.querySelectorAll('#activityTableBody tr');
      rows.forEach(r => {
        const text = r.innerText.toLowerCase();
        r.style.display = (!q || text.includes(q)) ? '' : 'none';
      });

      // Filtrar tarjetas de usuarios
      const cards = document.querySelectorAll('#activityUsersGrid .panel-box');
      cards.forEach(c => {
        const text = c.innerText.toLowerCase();
        c.style.display = (!q || text.includes(q)) ? 'flex' : 'none';
      });
    }

    function filterActivityModule(mod, el) {
      liveActivityModuleFilter = mod;
      document.querySelectorAll('#activityModuleChips .chip').forEach(c => c.classList.remove('active'));
      if (el) el.classList.add('active');
      fetchLiveActivity(true);
    }

    function filterActivityMethod(met, el) {
      liveActivityMethodFilter = met;
      document.querySelectorAll('#activityMethodChips .chip').forEach(c => c.classList.remove('active'));
      if (el) el.classList.add('active');
      fetchLiveActivity(true);
    }

    async function openTransactionDetailModal(id) {
      const modal = document.getElementById('transactionDetailModal');
      if (!modal) return;

      document.getElementById('modalTxUser').innerText = 'Cargando...';
      document.getElementById('modalTxRun').innerText = '...';
      document.getElementById('modalTxDate').innerText = '...';
      document.getElementById('modalTxIp').innerText = '...';
      document.getElementById('modalTxEndpoint').innerText = '...';
      document.getElementById('modalTxPayload').innerText = 'Consultando bitácora...';

      modal.style.display = 'flex';

      try {
        const res = await fetch(`/api/activity/detail?env=${encodeURIComponent(liveActivityEnv)}&id=${encodeURIComponent(id)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        currentViewingTransaction = data;

        document.getElementById('modalTxUser').innerText = data.nombre_completo || data.run_ejecutor || 'Desconocido';
        document.getElementById('modalTxRun').innerText = data.run_ejecutor || '-';
        document.getElementById('modalTxDate').innerText = data.fecha_ejecucion || '-';
        document.getElementById('modalTxIp').innerText = data.ip_ejecutor || '-';
        document.getElementById('modalTxEndpoint').innerText = `${data.metodo || 'POST'} ${data.url_endpoint || ''}`;

        const statusBadge = document.getElementById('modalTxStatusBadge');
        if (statusBadge) {
          statusBadge.outerHTML = getHttpStatusBadge(data.response_code);
        }

        const modBadge = document.getElementById('modalTxModuleBadge');
        if (modBadge) {
          const modStyle = getModuleBadgeStyle(data.modulo);
          modBadge.innerText = `${modStyle.icon} ${data.modulo || 'GENERAL'}`;
          modBadge.style.background = modStyle.bg;
          modBadge.style.borderColor = modStyle.border;
          modBadge.style.color = modStyle.color;
        }

        let payloadStr = data.transaccion || '(Sin payload o datos asociados)';
        try {
          if (payloadStr.startsWith('{') || payloadStr.startsWith('[')) {
            const normalized = payloadStr.replace(/'/g, '"').replace(/True/g, 'true').replace(/False/g, 'false').replace(/None/g, 'null');
            const parsed = JSON.parse(normalized);
            payloadStr = JSON.stringify(parsed, null, 2);
          }
        } catch (e) {
          // Keep raw string if parsing fails
        }

        document.getElementById('modalTxPayload').innerText = payloadStr;
      } catch (err) {
        document.getElementById('modalTxPayload').innerText = 'Error al cargar detalle: ' + err.message;
      }
    }

    function closeTransactionDetailModal() {
      const modal = document.getElementById('transactionDetailModal');
      if (modal) modal.style.display = 'none';
      currentViewingTransaction = null;
    }

    function copyTransactionPayload() {
      if (!currentViewingTransaction || !currentViewingTransaction.transaccion) {
        showToast('No hay datos para copiar.');
        return;
      }
      navigator.clipboard.writeText(currentViewingTransaction.transaccion);
      showToast('Payload copiado al portapapeles.');
    }

    let screenMirrorPollInterval = null;
    let currentMirrorUser = null;
    let knownMirrorDomVer = 0;
    let lastRenderedClickTimestamp = null;
    let currentRemoteW = 1920;
    let currentRemoteH = 1080;
    let isMirrorFullscreen = false;

    function changeMirrorScale(val) {
      applyMirrorViewportScale();
    }

    function toggleMirrorFullscreen() {
      const modalBox = document.getElementById('screenMirrorModalBox');
      const btn = document.getElementById('btnToggleMirrorFullscreen');
      if (!modalBox) return;
      isMirrorFullscreen = !isMirrorFullscreen;

      if (isMirrorFullscreen) {
        modalBox.style.maxWidth = '100vw';
        modalBox.style.width = '100vw';
        modalBox.style.height = '100vh';
        modalBox.style.margin = '0';
        modalBox.style.borderRadius = '0';
        modalBox.style.border = 'none';
        if (btn) btn.innerHTML = '🗗 Salir Pantalla Completa';
      } else {
        modalBox.style.maxWidth = '98vw';
        modalBox.style.width = '98vw';
        modalBox.style.height = '95vh';
        modalBox.style.margin = '2.5vh auto';
        modalBox.style.borderRadius = '12px';
        modalBox.style.border = '1px solid #d946ef';
        if (btn) btn.innerHTML = '⛶ Pantalla Completa';
      }

      setTimeout(applyMirrorViewportScale, 60);
    }

    function applyMirrorViewportScale() {
      const stage = document.getElementById('screenMirrorStage');
      const wrapper = document.getElementById('screenMirrorCanvasWrapper');
      const spacer = document.getElementById('screenMirrorCanvasSpacer');
      const scaleSelect = document.getElementById('mirrorScaleSelect');
      const scaleInfo = document.getElementById('mirrorScaleInfo');
      if (!stage || !wrapper) return;

      const mode = scaleSelect ? scaleSelect.value : 'fit';
      let s = 1.0;

      if (mode === 'fit') {
        const padX = 32;
        const padY = 32;
        const availW = Math.max(stage.clientWidth - padX, 320);
        const availH = Math.max(stage.clientHeight - padY, 240);
        const sx = availW / currentRemoteW;
        const sy = availH / currentRemoteH;
        s = Math.min(sx, sy);
        if (s > 1.0) s = 1.0;
      } else {
        s = parseFloat(mode) || 1.0;
      }

      wrapper.style.transform = `scale(${s})`;
      const scaledW = Math.round(currentRemoteW * s);
      const scaledH = Math.round(currentRemoteH * s);

      if (spacer) {
        spacer.style.width = `${scaledW}px`;
        spacer.style.height = `${scaledH + 24}px`;
      }
      if (scaleInfo) {
        scaleInfo.innerText = `${Math.round(s * 100)}%`;
      }
    }

    window.addEventListener('resize', () => {
      const modal = document.getElementById('screenMirrorModal');
      if (modal && modal.style.display === 'flex') {
        applyMirrorViewportScale();
      }
    });

    async function openScreenMirrorModal() {
      if (!connectedTrackingUser) {
        showToast('Debes estar en seguimiento de un usuario para abrir el espejo visual.');
        return;
      }

      const modal = document.getElementById('screenMirrorModal');
      const uName = document.getElementById('mirrorUserName');
      const emptyState = document.getElementById('screenMirrorEmptyState');
      const cursor = document.getElementById('screenMirrorCursor');
      const iframe = document.getElementById('screenMirrorIframe');

      if (!modal) return;
      currentMirrorUser = connectedTrackingUser.user_key || connectedTrackingUser.run;
      if (uName) uName.innerText = connectedTrackingUser.name || currentMirrorUser;
      
      modal.style.display = 'flex';
      if (emptyState) emptyState.style.display = 'flex';
      if (cursor) cursor.style.display = 'none';
      if (iframe) iframe.srcdoc = '';
      knownMirrorDomVer = 0;
      lastRenderedClickTimestamp = null;

      try {
        await fetch('/api/telemetry/mirror_control', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_key: currentMirrorUser, enabled: true })
        });
      } catch (e) {
        console.error('Error starting mirror subscription:', e);
      }

      if (screenMirrorPollInterval) clearInterval(screenMirrorPollInterval);
      pollScreenMirrorStream();
      screenMirrorPollInterval = setInterval(pollScreenMirrorStream, 250);
      setTimeout(applyMirrorViewportScale, 100);
    }

    async function closeScreenMirrorModal() {
      const modal = document.getElementById('screenMirrorModal');
      if (modal) modal.style.display = 'none';

      if (isMirrorFullscreen) {
        toggleMirrorFullscreen();
      }

      if (screenMirrorPollInterval) {
        clearInterval(screenMirrorPollInterval);
        screenMirrorPollInterval = null;
      }

      if (currentMirrorUser) {
        try {
          await fetch('/api/telemetry/mirror_control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_key: currentMirrorUser, enabled: false })
          });
        } catch (e) {
          console.error('Error stopping mirror subscription:', e);
        }
      }
      currentMirrorUser = null;
    }

    async function pollScreenMirrorStream() {
      if (!currentMirrorUser) return;
      try {
        const t0 = Date.now();
        const res = await fetch(`/api/telemetry/mirror_view?user=${encodeURIComponent(currentMirrorUser)}&known_ver=${knownMirrorDomVer}`);
        if (!res.ok) return;
        const data = await res.json();
        const mirror = data.mirror;

        const emptyState = document.getElementById('screenMirrorEmptyState');
        const cursor = document.getElementById('screenMirrorCursor');
        const iframe = document.getElementById('screenMirrorIframe');
        const wrapper = document.getElementById('screenMirrorCanvasWrapper');
        const resText = document.getElementById('mirrorResolutionText');
        const curCoords = document.getElementById('mirrorCursorCoords');
        const scrCoords = document.getElementById('mirrorScrollCoords');
        const fpsInd = document.getElementById('mirrorFpsIndicator');
        const statusEl = document.getElementById('mirrorTelemetryStatus');

        const latMs = Date.now() - t0;
        if (fpsInd) fpsInd.innerText = `${latMs}ms`;
        if (statusEl) statusEl.innerText = `Sondeo: ${new Date().toLocaleTimeString()}`;

        if (!mirror) {
          if (emptyState) emptyState.style.display = 'flex';
          if (cursor) cursor.style.display = 'none';
          return;
        }

        // Si tenemos DOM nuevo, renderizarlo en el iframe
        if (mirror.dom_html) {
          if (emptyState) emptyState.style.display = 'none';
          if (iframe) iframe.srcdoc = mirror.dom_html;
          if (mirror.dom_ver) knownMirrorDomVer = mirror.dom_ver;
        } else if (knownMirrorDomVer > 0) {
          if (emptyState) emptyState.style.display = 'none';
        }

        // Dimensionar el canvas a la resolución exacta del usuario
        const rw = mirror.window_w || 1920;
        const rh = mirror.window_h || 1080;
        if (rw !== currentRemoteW || rh !== currentRemoteH) {
          currentRemoteW = rw;
          currentRemoteH = rh;
          if (wrapper) {
            wrapper.style.width = `${currentRemoteW}px`;
            wrapper.style.height = `${currentRemoteH}px`;
          }
          applyMirrorViewportScale();
        }

        // Scroll sync en el iframe
        if (iframe && iframe.contentWindow && (mirror.scroll_x !== undefined || mirror.scroll_y !== undefined)) {
          try {
            iframe.contentWindow.scrollTo(mirror.scroll_x || 0, mirror.scroll_y || 0);
          } catch(e) {}
        }

        // Puntero rojo virtual exacto (al estar dentro del canvas escalado, coincide 1:1)
        if (cursor && mirror.cursor_x !== undefined && mirror.cursor_y !== undefined) {
          cursor.style.display = 'block';
          cursor.style.left = `${mirror.cursor_x}px`;
          cursor.style.top = `${mirror.cursor_y}px`;
        }

        // Pulso de click
        if (mirror.last_click && mirror.last_click.timestamp && mirror.last_click.timestamp !== lastRenderedClickTimestamp) {
          lastRenderedClickTimestamp = mirror.last_click.timestamp;
          triggerMirrorClickPulse(mirror.last_click.x, mirror.last_click.y);
        }

        if (resText) resText.innerText = `${currentRemoteW}x${currentRemoteH}`;
        if (curCoords) curCoords.innerText = `(${mirror.cursor_x || 0}, ${mirror.cursor_y || 0})`;
        if (scrCoords) scrCoords.innerText = `(${mirror.scroll_x || 0}, ${mirror.scroll_y || 0})`;

      } catch (err) {
        console.error('Error polling mirror stream:', err);
      }
    }

    function triggerMirrorClickPulse(x, y) {
      const pulse = document.getElementById('screenMirrorClickPulse');
      if (!pulse) return;
      pulse.style.left = `${x}px`;
      pulse.style.top = `${y}px`;
      pulse.style.transform = 'translate(-50%, -50%) scale(0)';
      pulse.style.opacity = '1';

      requestAnimationFrame(() => {
        pulse.style.transform = 'translate(-50%, -50%) scale(1.6)';
        pulse.style.opacity = '0';
      });
    }

    function forceMirrorRefresh() {
      knownMirrorDomVer = 0;
      pollScreenMirrorStream();
      showToast('🔄 Solicitando snapshot DOM actualizado al usuario...');
    }


    // -------------------------------------------------------------------------
    // Pestaña «Sitio»: configuración por entorno (tema estacional + manifiestos)
    // -------------------------------------------------------------------------
    let siteCarpetaElegida = null;
    /** Último /api/site/config leído (para encadenar y para atajos de la pestaña Sitio). */
    let siteConfigCache = null;

    /** Muestra el «x» sólo cuando hay texto que limpiar. */
    function refrescarBotonLimpiarBusqueda() {
      const inp = document.getElementById('consoleServiceSearch');
      const btn = document.getElementById('consoleServiceClear');
      if (btn) btn.hidden = !(inp && inp.value.trim());
    }

    /** Vacía la búsqueda de consolas y repinta el muro. */
    function limpiarBusquedaConsolas() {
      const inp = document.getElementById('consoleServiceSearch');
      if (inp) {
        inp.value = '';
        inp.focus();
      }
      consoleWorkspace.nameFilter = '';
      refrescarBotonLimpiarBusqueda();
      renderConsoleStage();
    }

    function siteEnvActual() {
      const sel = document.getElementById('siteEnvSelect');
      return (sel && sel.value) || 'develop';
    }

    function onSiteEnvChange(env) {
      loadSiteConfig(env);
      /* El tema estacional es por entorno: al cambiar de entorno hay que releerlo. */
      if (typeof fetchCurrentK8sTheme === 'function') fetchCurrentK8sTheme();
    }

    /** Entorno de la pestaña Deployments: es el que rige la carpeta de YAML. */
    function manifestDirEnv() {
      const sel = document.getElementById('deployEnvSelect');
      return (sel && sel.value) || 'develop';
    }

    function openManifestDirModal() {
      const modal = document.getElementById('manifestDirModal');
      if (!modal) return;
      if (typeof ensureDevOrAdminAuth === 'function' && !ensureDevOrAdminAuth()) return;
      const env = manifestDirEnv();
      const lbl = document.getElementById('manifestDirEnv');
      if (lbl) lbl.textContent = env.toUpperCase();
      const panel = document.getElementById('siteBrowsePanel');
      if (panel) { panel.style.display = 'none'; panel.innerHTML = ''; }
      siteCarpetaElegida = null;
      const btn = document.getElementById('siteK8sUseBtn');
      if (btn) { btn.disabled = true; btn.textContent = '\u2705 Usar esta carpeta'; }
      modal.style.display = 'flex';
      /* La carpeta es por entorno: se lee la del entorno elegido en Deployments
         y se abre ya explorando la vigente, para que el destino sea evidente y
         no se acabe fijando la raíz del workspace por accidente. */
      loadSiteConfig(env, { desdeModal: true }).then(() => {
        const actual = (siteConfigCache && siteConfigCache.k8s_dir_abs) || '';
        if (actual) siteBrowseTo(actual);
      });
    }

    function closeManifestDirModal() {
      const modal = document.getElementById('manifestDirModal');
      if (modal) modal.style.display = 'none';
    }

    async function loadSiteConfig(env, opciones = {}) {
      const objetivo = env || siteEnvActual();
      try {
        const res = await fetch('/api/site/config?env=' + encodeURIComponent(objetivo));
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        siteConfigCache = data;
        renderSiteConfig(data, opciones);
        return data;
      } catch (err) {
        showToast('\u26a0\ufe0f No se pudo cargar la configuraci\u00f3n del sitio: ' + err.message);
        return null;
      }
    }

    function renderSiteConfig(d, opciones = {}) {
      if (!d || !d.env) return;
      const sel = document.getElementById('siteEnvSelect');
      if (sel && !sel.options.length) {
        sel.innerHTML = (d.entornos || []).map((e) =>
          `<option value="${escapeHtml(e)}">${escapeHtml(String(e).toUpperCase())}</option>`).join('');
        sel.value = d.env;
      }
      if (opciones.desdeModal) {
        /* El modal trabaja con el entorno de Deployments: no debe mover el
           selector de Sitio ni el tema que se está viendo allí. */
        const lbl = document.getElementById('manifestDirEnv');
        if (lbl) lbl.textContent = String(d.label || d.env).toUpperCase();
      } else {
        const badge = document.getElementById('siteEnvBadge');
        if (badge) badge.textContent = String(d.label || d.env).toUpperCase();
      }

      const dir = document.getElementById('siteK8sDir');
      if (dir) {
        dir.textContent = d.k8s_dir + (d.exists ? '' : '  (no existe)');
        dir.title = d.k8s_dir_abs;
        dir.style.color = d.exists ? 'var(--accent)' : 'var(--warn)';
      }
      const inv = document.getElementById('siteInventory');
      if (inv) inv.innerHTML = siteInventoryHtml(d);

      /* El tema estacional es por entorno: se relee con el entorno elegido de
         Sitio (no cuando el modal de manifiestos pidió los datos). */
      if (!opciones.desdeModal && typeof fetchCurrentK8sTheme === 'function') fetchCurrentK8sTheme();
    }

    /** Filtro vigente del árbol de manifiestos (se conserva entre repintados). */
    let siteYamlFiltro = '';

    function siteInventoryHtml(d) {
      const archivos = d.yaml || [];
      const porServicio = new Map((d.esperados || []).map((e) => [e.file, e.service]));

      /* Se agrupan TODOS los manifiestos encontrados, no sólo los del catálogo:
         antes la vista mostraba los recuentos, los que faltaban y unos pocos
         «extras» filtrados por prefijo, así que de 45 ficheros se veían ~11. */
      const grupos = new Map();
      archivos.forEach((f) => {
        const i = f.rel.lastIndexOf('/');
        const carpeta = i === -1 ? '.' : f.rel.slice(0, i);
        if (!grupos.has(carpeta)) grupos.set(carpeta, []);
        grupos.get(carpeta).push(f);
      });

      const bloques = Array.from(grupos.entries())
        .sort((x, y) => (x[0] === '.' ? -1 : y[0] === '.' ? 1 : x[0].localeCompare(y[0])))
        .map(([carpeta, files]) => `
          <details open class="site-yaml-folder" style="margin-top:6px;">
            <summary style="cursor:pointer; font-size:12px; font-weight:700;">
              &#128193; ${escapeHtml(carpeta)}
              <span style="color:var(--text-muted); font-weight:400;">(${files.length})</span>
            </summary>
            <div style="display:flex; flex-direction:column; gap:2px; margin:6px 0 2px 18px;">
              ${files.map((f) => {
                const svc = porServicio.get(f.rel);
                return `<div class="site-yaml-row" data-yaml="${escapeHtml((f.rel + ' ' + (svc || '')).toLowerCase())}"
                          style="display:flex; align-items:center; gap:8px; font-size:11.5px; flex-wrap:wrap;">
                  <span style="font-family:ui-monospace, monospace; color:${svc ? 'var(--text)' : 'var(--text-muted)'};">${escapeHtml(f.name)}</span>
                  <span style="font-size:10px; color:var(--text-muted);">${(f.size / 1024).toFixed(1)} KB</span>
                  ${svc
                    ? `<span class="badge-pill" style="font-size:9.5px; background:rgba(56,189,248,0.14); border:1px solid var(--card-border); color:var(--accent);">${escapeHtml(svc)}</span>`
                    : '<span class="badge-pill" style="font-size:9.5px; background:rgba(148,163,184,0.12); border:1px solid var(--card-border); color:var(--text-muted);">extra</span>'}
                </div>`;
              }).join('')}
            </div>
          </details>`).join('');

      const faltan = d.faltantes || [];
      const faltanHtml = faltan.length
        ? `<div style="margin-top:8px; font-size:11.5px; color:var(--warn);">
             <b>Faltan ${faltan.length} del cat&aacute;logo:</b>
             ${faltan.map((f) => `<code>${escapeHtml(f.file)}</code>`).join(', ')}
           </div>`
        : `<div style="margin-top:8px; font-size:11.5px; color:var(--ok);">El cat&aacute;logo tiene todos sus YAML en esta carpeta.</div>`;

      return `
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
          <div style="font-size:12px;">
            <b>${archivos.length}</b> manifiestos en <b>${grupos.size}</b> carpeta(s)
          </div>
          <span class="badge-pill" style="background:rgba(56,189,248,0.14); border:1px solid var(--card-border); font-size:10.5px;">
            ${d.esperados_presentes}/${d.esperados_total} del cat&aacute;logo
          </span>
          <input type="search" class="search-input" id="siteYamlFiltroInput"
                 style="margin-left:auto; padding:4px 10px; font-size:11.5px; max-width:260px;"
                 placeholder="Filtrar por fichero o servicio..."
                 value="${escapeHtml(siteYamlFiltro)}" oninput="siteFiltrarYaml(this.value)">
        </div>
        ${faltanHtml}
        <!-- Sin scroll interno: el modal ya desplaza, así no queda nada oculto
             en una zona con scroll propia que parecía "no mostrar todo". -->
        <div id="siteYamlArbol" style="margin-top:8px;">
          ${bloques || '<span style="font-size:11.5px; color:var(--text-muted);">No hay manifiestos (.yaml/.yml) en esta carpeta.</span>'}
        </div>`;
    }

    /** Filtra el árbol sin repintarlo (así no se pierde el foco ni el scroll). */
    function siteFiltrarYaml(texto) {
      siteYamlFiltro = texto || '';
      const q = siteYamlFiltro.trim().toLowerCase();
      const arbol = document.getElementById('siteYamlArbol');
      if (!arbol) return;
      arbol.querySelectorAll('.site-yaml-row').forEach((row) => {
        row.style.display = (!q || (row.dataset.yaml || '').includes(q)) ? '' : 'none';
      });
      arbol.querySelectorAll('details.site-yaml-folder').forEach((det) => {
        const visibles = Array.from(det.querySelectorAll('.site-yaml-row'))
          .filter((r) => r.style.display !== 'none').length;
        det.style.display = visibles ? '' : 'none';
        if (q) det.open = true;
      });
    }

    /** Pinta el veredicto de la carpeta y el estado del botón «Usar».

        (Se perdió en una reescritura anterior del inventario y el explorador
        fallaba en silencio: `siteBrowseTo` lo llamaba dentro de su `try`.)
    */
    function pintarVeredictoCarpeta(d) {
      const btn = document.getElementById('siteK8sUseBtn');
      const sirve = (d.esperados || 0) > 0;
      const total = d.esperados_total || 0;
      if (btn) {
        btn.disabled = !sirve;
        btn.textContent = sirve
          ? `\u2705 Usar esta carpeta (${d.esperados}/${total})`
          : '\u2705 Usar esta carpeta';
        btn.title = sirve
          ? `Fijar ${d.path} para este entorno`
          : `Aquí no está ninguno de los ${total} manifiestos del catálogo`;
      }
      return { sirve, total };
    }

    /** Abre el explorador en la carpeta vigente o en la que se está mirando. */
    function siteExplorarActual() {
      const destino = siteCarpetaElegida || (siteConfigCache && siteConfigCache.k8s_dir_abs) || '';
      siteBrowseTo(destino);
    }

    async function siteBrowseTo(path) {
      const panel = document.getElementById('siteBrowsePanel');
      try {
        const res = await fetch('/api/site/browse?path=' + encodeURIComponent(path || ''));
        const d = await res.json();
        if (!panel) return;
        panel.style.display = '';
        if (!d.valid) {
          panel.innerHTML = `<div style="color:var(--danger); font-size:12px;">${escapeHtml(d.error || 'Ruta inválida')}</div>`;
          return;
        }
        /* Navegar y ELEGIR son cosas distintas: aquí se navega.  La carpeta a
           fijar se dice explícitamente y sólo se habilita si contiene los
           manifiestos del catálogo (un padre tipo `k8s/` da 0 y no vale). */
        siteCarpetaElegida = d.path;
        const { sirve, total } = pintarVeredictoCarpeta(d);
        const veredicto = sirve
          ? `<span style="color:var(--ok); font-weight:700;">${d.esperados} de ${total} manifiestos del catálogo están aquí</span>`
          : `<span style="color:var(--warn); font-weight:700;">ninguno de los ${total} manifiestos del catálogo está en este nivel</span>`
            + `<span style="color:var(--text-muted);"> — el despliegue los busca aquí mismo; entra en la subcarpeta del entorno</span>`;

        /* Árbol completo bajo esta carpeta (no sólo el nivel actual): en
           `backend/` se veían sólo `ms_*` y en `frontend/` sólo `mf_*`, así que
           parecía que faltaban ficheros.  Se agrupa por primera carpeta. */
        const arbol = d.tree || [];
        const gruposArbol = new Map();
        arbol.forEach((f) => {
          const i = f.rel.indexOf('/');
          const grupo = i === -1 ? '.' : f.rel.slice(0, i);
          if (!gruposArbol.has(grupo)) gruposArbol.set(grupo, []);
          gruposArbol.get(grupo).push(f);
        });
        const listaFicheros = arbol.length
          ? `<div style="margin-top:12px;">
               <div style="font-size:11px; color:var(--text-muted);">
                 Todos los manifiestos de este &aacute;rbol (<b>${arbol.length}</b>):
               </div>
               <div style="margin-top:6px; display:flex; flex-direction:column; gap:2px;">
                 ${Array.from(gruposArbol.entries())
                   .sort((x, y) => (x[0] === '.' ? -1 : y[0] === '.' ? 1 : x[0].localeCompare(y[0])))
                   .map(([grupo, files]) => `
                     <div style="font-size:11.5px; font-weight:700; color:var(--text-muted); margin-top:4px;">
                       &#128193; ${escapeHtml(grupo)} (${files.length})
                     </div>
                     ${files.map((f) => `<div style="font-size:11.5px; font-family:ui-monospace, monospace; display:flex; gap:8px; margin-left:14px;">
                         <span>${escapeHtml(f.rel)}</span>
                         <span style="color:var(--text-muted); font-size:10px;">${(f.size / 1024).toFixed(1)} KB</span>
                       </div>`).join('')}`).join('')}
               </div>
             </div>`
          : '';

        const filas = (d.dirs || []).map((x) => {
          const ok = x.esperados > 0;
          const detalle = ok
            ? `<span style="color:var(--ok);">${x.esperados}/${x.esperados_total} del cat&aacute;logo</span>`
            : (x.yaml ? `<span style="color:var(--text-muted);">${x.yaml} YAML</span>` : '<span style="color:var(--text-muted);">sin YAML</span>');
          return `<div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <button class="btn btn-sm btn-outline" style="font-size:11px;" data-site-dir="${escapeHtml(x.path)}"
                    title="Entrar en ${escapeHtml(x.name)}">&#128193; ${escapeHtml(x.name)}</button>
            ${detalle}
            ${ok ? `<button class="btn btn-sm" style="font-size:11px; background:var(--accent-hover); color:var(--text);"
                    data-site-usar="${escapeHtml(x.path)}" title="Fijar esta carpeta sin entrar">&#10004; usar &eacute;sta</button>` : ''}
          </div>`;
        }).join('');

        panel.innerHTML = `
          <div style="background:rgba(56,189,248,0.08); border:1px solid var(--card-border); border-radius:8px; padding:10px 12px;">
            <div style="font-size:11.5px;">
              Carpeta a fijar: <code style="color:var(--accent);">${escapeHtml(d.path)}</code>
            </div>
            <div style="font-size:11.5px; margin-top:4px;">${veredicto}</div>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; align-items:center;">
            <button class="btn btn-sm btn-outline" style="font-size:11px;" data-site-dir="${escapeHtml(d.parent)}">&#11014; Subir</button>
            <span style="font-size:11px; color:var(--text-muted);">Subcarpetas:</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px; margin-top:8px;">${filas || '<span style="font-size:11.5px; color:var(--text-muted);">No hay subcarpetas.</span>'}</div>
          ${listaFicheros}`;

        panel.querySelectorAll('[data-site-dir]').forEach((b) => {
          b.addEventListener('click', () => siteBrowseTo(b.dataset.siteDir));
        });
        /* «usar ésta» fija la carpeta sin navegar dentro (y sin ambigüedad). */
        panel.querySelectorAll('[data-site-usar]').forEach((b) => {
          b.addEventListener('click', async () => {
            const destino = b.dataset.siteUsar;
            /* Se entra en la carpeta elegida para que el veredicto y el botón
               principal queden apuntando a ELLA (antes seguían en el padre). */
            await siteBrowseTo(destino);
            const ok = confirm(`¿Fijar la carpeta de manifiestos en:\n${destino}?`);
            if (ok) siteUseCurrentDir();
          });
        });
        if (!sirve) showToast('\u2139\ufe0f Esa carpeta no contiene los manifiestos; usa «\u2714 usar ésta» en la subcarpeta del entorno.');
      } catch (err) {
        showToast('\u26a0\ufe0f No se pudo explorar la carpeta: ' + err.message);
      }
    }

    async function siteUseCurrentDir() {
      if (!siteCarpetaElegida) {
        showToast('\u26a0\ufe0f Primero explora y elige una carpeta.');
        return;
      }
      if (!ensureDevOrAdminAuth()) return;
      const modalAbierto = (document.getElementById('manifestDirModal') || {}).style?.display === 'flex';
      const env = modalAbierto ? manifestDirEnv() : siteEnvActual();
      if (!confirm(`\u00bfFijar la carpeta de manifiestos de ${env.toUpperCase()} en:\n${siteCarpetaElegida}?`)) return;
      try {
        const res = await fetch('/api/site/k8s_dir', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ env: env, path: siteCarpetaElegida })
        });
        const data = await res.json();
        if (data.success) {
          showToast('\u2705 ' + data.message);
          if (data.config) renderSiteConfig(data.config, { desdeModal: env === manifestDirEnv() });
          /* La matriz de Despliegues lee de esa carpeta: se repinta con la nueva. */
          if (typeof fetchDeploymentVersions === 'function') fetchDeploymentVersions();
        } else {
          showToast('\u26a0\ufe0f ' + (data.message || 'No se pudo guardar la carpeta'));
        }
      } catch (err) {
        showToast('\u26a0\ufe0f ' + err.message);
      }
    }

    window.addEventListener('DOMContentLoaded', () => {
      // Restaurar estado colapsado guardado en localStorage
      if (localStorage.getItem('sisper_sidebar_collapsed') === 'true' && window.innerWidth > 1024) {
        document.getElementById('sidebarNav')?.classList.add('collapsed');
      }
      updateRoleUI();
      validateAuthSession();
      fetchStatus();
      renderInfraMatrix();
      toggleActivityAutoRefresh();
      fetchK8sStatus();
      if (typeof initConsoleWorkspace === 'function') {
        initConsoleWorkspace();
      }
      setInterval(fetchStatus, 3000);
    });
