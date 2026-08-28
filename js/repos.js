'use strict';

/* ================= 可调配置 ================= */
const USERNAME = 'ABitGinger';          // GitHub 用户名
const SHOW_FORKS = true;                // 是否展示 fork 来的仓库（改为 false 即隐藏）
const EXCLUDE_REPOS = ['ABitGinger'];   // 不展示的仓库名（个人资料配置仓库）
const DATA_URL = '/repos/repos.json';   // 仓库数据（部署时由 GitHub Actions 生成）
const PREVIEW_DIR = '/repos/previews/'; // 预览图目录（同上，与数据一起生成）
                                        // 手动指定某仓库图片：编辑 repos/overrides.json（键为仓库名，值为路径或 URL）

/* 数据与预览图均在部署时生成（.github/workflows/static.yml → .github/scripts/build_repos.py），
   页面只加载同源静态文件，不请求 GitHub 公共 API，无任何限流问题。 */

/* ================= 工具 ================= */
function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
}

/* ================= 数据 ================= */
async function loadRepos() {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error('展示数据响应异常：' + res.status);
    const data = await res.json();
    return Array.isArray(data.repos) ? data.repos : [];
}

function visibleRepos(list) {
    return list
        .filter(repo => !EXCLUDE_REPOS.includes(repo.name))
        .filter(repo => SHOW_FORKS || !repo.fork)
        .sort((a, b) =>
            (b.stargazers_count - a.stargazers_count) ||
            (new Date(b.pushed_at) - new Date(a.pushed_at))
        );
}

/* ================= 渲染 ================= */
function buildCard(repo) {
    const card = el('a', 'repo-card');
    card.href = repo.html_url;
    card.target = '_blank';
    card.rel = 'noopener';

    // 顶部图片：优先用手动覆盖图（repos/overrides.json），失败回退到生成图，再失败是占位块
    const imgWrap = el('div', 'repo-card-imgwrap');
    const img = document.createElement('img');
    img.className = 'repo-card-img';
    img.src = repo.image || PREVIEW_DIR + repo.name + '.png';
    img.alt = repo.name + ' 预览图';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
        if (repo.image && !img.dataset.fallback) {
            img.dataset.fallback = '1';
            img.src = PREVIEW_DIR + repo.name + '.png';
        } else {
            imgWrap.replaceChildren(el('div', 'repo-img-fallback', '📦'));
        }
    });
    imgWrap.append(img);
    if (repo.fork) imgWrap.append(el('span', 'repo-badge', 'Fork'));
    if (repo.archived) imgWrap.append(el('span', 'repo-badge repo-badge-archived', '已归档'));

    const body = el('div', 'repo-card-body');
    body.append(el('h3', 'repo-card-title', repo.name));
    body.append(el('p', 'repo-desc', repo.description || '暂无简介'));

    const topics = (repo.topics || []).slice(0, 3);
    if (topics.length) {
        const tags = el('div', 'repo-tags');
        topics.forEach(topic => tags.append(el('span', 'repo-tag', topic)));
        body.append(tags);
    }

    const meta = el('div', 'repo-meta');
    if (repo.language) {
        const lang = el('span', 'repo-lang');
        const dot = el('span', 'lang-dot');
        dot.style.backgroundColor = repo.lang_color || '#8b949e';
        lang.append(dot, document.createTextNode(repo.language));
        meta.append(lang);
    }
    meta.append(el('span', 'repo-stars', '⭐ ' + (repo.stargazers_count || 0)));
    if (repo.homepage) meta.append(el('span', 'repo-home', '🏠 主页'));
    meta.append(el('span', 'repo-updated', '更新于 ' + (repo.pushed_at || '').slice(0, 10)));
    body.append(meta);

    card.append(imgWrap, body);
    return card;
}

async function renderRepos() {
    const grid = document.getElementById('repo-grid');
    const status = document.getElementById('repo-status');
    const summary = document.getElementById('repo-summary');
    if (!grid) return;

    // 骨架屏
    grid.replaceChildren(...Array.from({ length: 4 }, () => el('div', 'repo-skeleton')));
    if (status) {
        status.hidden = true;
        status.replaceChildren();
    }

    try {
        const repos = await loadRepos();
        const list = visibleRepos(repos);
        grid.replaceChildren(...list.map(buildCard));
        if (summary) {
            summary.textContent = `共 ${list.length} 个仓库 · 点击卡片可跳转到仓库主页`;
        }
    } catch (err) {
        grid.replaceChildren();
        if (summary) summary.textContent = '';
        if (status) {
            const msg = el('p', null, '😔 展示数据加载失败，请稍后重试。');
            const retry = el('button', 'button', '🔄 重试');
            retry.type = 'button';
            retry.addEventListener('click', renderRepos);
            const ghLink = el('a', 'button', '前往 GitHub 主页');
            ghLink.href = `https://github.com/${USERNAME}?tab=repositories`;
            ghLink.target = '_blank';
            ghLink.rel = 'noopener';
            status.replaceChildren(msg, retry, ghLink);
            status.hidden = false;
        }
    }
}

/* 展示视图初始化：直接访问 /repos/ 时由 DOMContentLoaded 触发；
   从主页静默跳转过来时由 view:swapped 事件触发（详见 js/script.js） */
function bootReposView() {
    const grid = document.getElementById('repo-grid');
    if (!grid || grid.dataset.booted) return;
    grid.dataset.booted = '1';
    renderRepos();
}

document.addEventListener('DOMContentLoaded', bootReposView);
document.addEventListener('view:swapped', bootReposView);
