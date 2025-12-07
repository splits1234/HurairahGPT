const passwordInput = document.getElementById("password");
      const togglePassword = document.getElementById("toggle-password");
      togglePassword.addEventListener("click", () => {
        const type = passwordInput.type === "password" ? "text" : "password";
        passwordInput.type = type;
        togglePassword.textContent = type === "password" ? "Show" : "Hide";
      });

      const form = document.getElementById("login-form");
      const submitBtn = document.getElementById("submit-btn");
      const emailInput = document.getElementById("email");
      const emailError = document.getElementById("email-error");
      const passwordError = document.getElementById("password-error");

      function validateEmail(email) {
        return /\S+@\S+\.\S+/.test(email);
      }

      form.addEventListener("submit", (e) => {
        e.preventDefault();
        let valid = true;

        if (!validateEmail(emailInput.value.trim())) {
          emailError.style.display = "block";
          valid = false;
        } else {
          emailError.style.display = "none";
        }

        if (passwordInput.value.length < 4) {
          passwordError.style.display = "block";
          valid = false;
        } else {
          passwordError.style.display = "none";
        }

        if (!valid) return;

        submitBtn.disabled = true;
        submitBtn.classList.add("loading");
        setTimeout(() => form.submit(), 600);
      });