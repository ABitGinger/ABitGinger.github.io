document.addEventListener('DOMContentLoaded', function() {
    var emailText = document.getElementById('email-text');
    var emailToCopy = 'abitginger@foxmail.com';

    emailText.addEventListener('mouseover', function() {
        // 鼠标悬停时显示“点击复制”
        this.textContent = '📋复制地址';
    });

    emailText.addEventListener('mouseout', function() {
        // 鼠标离开时恢复原文本
        this.textContent = '📧发送邮件';
    });

    emailText.addEventListener('click', function() {
        // 点击时复制文本到剪贴板
        navigator.clipboard.writeText(emailToCopy).then(function() {
            // 复制成功后的回调
            this.textContent = '复制成功✔️';
            // 可以选择在这里改变文本或显示一个检查标记等
        }.bind(emailText)).catch(function(err) {
            // 复制失败的错误处理
            this.textContent = '复制失败❌';
        }.bind(emailText));
    });
});