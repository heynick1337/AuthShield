// Some browsers autofill credentials without firing the normal 'input' event,
// which kept the submit button disabled even when fields were filled.
// Fix: the CSS triggers a tiny animation on autofilled inputs, which we
// listen for here, then re-run validation to enable the button.
document.addEventListener('animationstart', function (e) {
  if (e.animationName === 'onAutoFillStart') {
    validateEmail(false);
    validatePassword(false);
  }
}, true);

// Extra fallback: poll for a short time after load in case the browser
// applies autofill late (e.g. Firefox, some password managers).
window.addEventListener('load', function () {
  let checks = 0;
  const interval = setInterval(function () {
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    if (email.value || password.value) {
      validateEmail(false);
      validatePassword(false);
    }
    if (++checks >= 20) clearInterval(interval);
  }, 100);
});

function validateEmail(showError) {
  const emailInput = document.getElementById('email');
  const emailError = document.getElementById('email-error');
  const passwordInput = document.getElementById('password');
  const submitButton = document.getElementById('submit-button');

  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isValid = pattern.test(emailInput.value);

  submitButton.disabled = !(emailInput.value && passwordInput.value);

  if (showError && !isValid) {
    emailError.classList.remove('hidden');
    emailInput.classList.add('invalid');
  } else if (isValid) {
    emailError.classList.add('hidden');
    emailInput.classList.remove('invalid');
  }
}

function validatePassword(showError) {
  const passwordInput = document.getElementById('password');
  const passwordError = document.getElementById('password-error');
  const emailInput = document.getElementById('email');
  const submitButton = document.getElementById('submit-button');

  const isValid = passwordInput.value.length >= 8;
  submitButton.disabled = !(emailInput.value && passwordInput.value);

  if (showError && !isValid) {
    passwordError.classList.remove('hidden');
    passwordInput.classList.add('invalid');
  } else if (isValid) {
    passwordError.classList.add('hidden');
    passwordInput.classList.remove('invalid');
  }
}

function submitLogin(event) {
  event.preventDefault();

  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const submitText = document.getElementById('submit-text');
  const submitSpinner = document.getElementById('submit-spinner');

  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const validEmail = pattern.test(emailInput.value);
  const validPassword = passwordInput.value.length >= 8;

  validateEmail(true);
  validatePassword(true);

  if (validEmail && validPassword) {
    submitText.classList.add('hidden');
    submitSpinner.classList.remove('hidden');
    event.target.submit();
  }
}

document.getElementById('email').addEventListener('blur', function () { validateEmail(true); });
document.getElementById('email').addEventListener('input', function () { validateEmail(false); });
document.getElementById('password').addEventListener('input', function () { validatePassword(false); });
document.getElementById('loginForm').addEventListener('submit', submitLogin);
