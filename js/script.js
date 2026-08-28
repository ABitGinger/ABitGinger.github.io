'use strict';

/* ---------- 页脚邮箱复制 ---------- */
document.addEventListener('DOMContentLoaded', function () {
    var emailText = document.getElementById('email-text');
    if (!emailText) return;
    var emailToCopy = 'abitginger@foxmail.com';

    emailText.addEventListener('mouseover', function () {
        this.textContent = '📋复制地址';
    });

    emailText.addEventListener('mouseout', function () {
        this.textContent = '📧发送邮件';
    });

    emailText.addEventListener('click', function () {
        navigator.clipboard.writeText(emailToCopy).then(function () {
            emailText.textContent = '复制成功✔️';
        }).catch(function () {
            emailText.textContent = '复制失败❌';
        });
    });
});

/* ---------- 站内静默跳转 ----------
   带 data-silent 的链接（主页「仓库展示」按钮、展示页「返回主页」）：
   fetch 目标页并只替换 <main>，pushState 更新地址栏，页眉页脚背景均不动，
   因此不刷新页面；对应路径（/repos/）也是真实存在的静态页，直接访问同样有效。
   fetch 或解析失败时回退为普通整页跳转。 */
document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var link = e.target.closest('a[data-silent]');
    if (!link || link.target === '_blank') return;
    var url = new URL(link.href, location.href);
    if (url.origin !== location.origin) return;
    e.preventDefault();
    silentNavigate(url.href, true);
});

window.addEventListener('popstate', function () {
    silentNavigate(location.href, false);
});

async function silentNavigate(url, push) {
    try {
        var res = await fetch(url);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var doc = new DOMParser().parseFromString(await res.text(), 'text/html');
        var nextMain = doc.querySelector('main');
        var curMain = document.querySelector('main');
        if (!nextMain || !curMain) throw new Error('页面缺少 main 元素');
        nextMain.classList.add('view-enter');
        curMain.replaceWith(nextMain);
        document.title = doc.title;
        if (push) history.pushState({}, '', url);
        window.scrollTo(0, 0);
        // 通知各模块初始化新视图（仓库列表的渲染见 js/repos.js）
        document.dispatchEvent(new CustomEvent('view:swapped'));
    } catch (err) {
        location.href = url;
    }
}
