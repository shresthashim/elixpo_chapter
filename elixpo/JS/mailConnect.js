document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector('form');
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = form.querySelector('input[name="name"]').value.trim();
        const email = form.querySelector('input[name="email"]').value.trim();
        const message = form.querySelector('textarea[name="message"]').value.trim();

        if (!name || !email || !message) {
            showToast("Please fill in all fields.", 3000);
            return;
        }

        // Disable button to prevent multiple submits
        const submitBtn = form.querySelector('.submitButton');
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";

        try {
            const res = await fetch("/api/mail", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, message })
            });

            const data = await res.json();

            if (res.ok && data.success) {
                showToast("Message sent successfully!", 3000);
                form.reset();
            } else {
                alert(data.error || "Failed to send message. Please try again later.");
            }
        } catch (err) {
            showToast("Failed to send message. Please try again later.", 5000);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Send";
        }
    });
});

function showToast(message, duration = 3000) {
    const toast = document.getElementById('toastNotification');
    toast.querySelector('span').textContent = message;
    toast.classList.remove('opacity-0', 'pointer-events-none');
    toast.classList.add('opacity-100');
    setTimeout(() => {
        toast.classList.remove('opacity-100');
        toast.classList.add('opacity-0', 'pointer-events-none');
    }, duration);
}