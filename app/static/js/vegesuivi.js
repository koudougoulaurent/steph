/**
 * VégéSuivi Pro — Scripts utilitaires
 * Direction Régionale de l'Environnement
 */

/* ─── Récupération du token CSRF depuis la balise meta ──── */
function getCsrfToken() {
  var meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

/* ─── Auto-injection CSRF dans tous les formulaires POST ── */
function injectCsrfToForms() {
  document.querySelectorAll('form[method="POST"], form[method="post"]').forEach(function (form) {
    if (!form.querySelector('input[name="csrf_token"]')) {
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'csrf_token';
      input.value = getCsrfToken();
      form.prepend(input);
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {

  /* Injecter le CSRF dans tous les formulaires de la page */
  injectCsrfToForms();

  /* ─── Fermeture automatique des alertes flash après 6 s ─── */
  document.querySelectorAll('.alert.alert-dismissible').forEach(function (el) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });

  /* ─── Confirmation avant suppression / désactivation ─── */
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      var msg = el.getAttribute('data-confirm') || 'Confirmer cette action ?';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  /* ─── Affichage / masquage du mot de passe ─── */
  document.querySelectorAll('[data-toggle-pwd]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var targetId = btn.getAttribute('data-toggle-pwd');
      var input = document.getElementById(targetId);
      if (!input) return;
      var isText = input.type === 'text';
      input.type = isText ? 'password' : 'text';
      var icon = btn.querySelector('i');
      if (icon) icon.className = isText ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
  });

  /* ─── Mise en évidence du lien de nav actif ─── */
  var path = window.location.pathname.split('/')[1] || '';
  document.querySelectorAll('.navbar .nav-link').forEach(function (link) {
    var href = link.getAttribute('href') || '';
    var section = href.split('/')[1] || '';
    if (section && section === path) link.classList.add('active');
  });

  /* ─── Compteur de caractères pour les textareas ─── */
  document.querySelectorAll('textarea[maxlength]').forEach(function (ta) {
    var maxLen = parseInt(ta.getAttribute('maxlength'), 10);
    var counter = document.createElement('small');
    counter.className = 'form-text text-end d-block text-muted';
    counter.textContent = '0 / ' + maxLen + ' caractères';
    ta.parentNode.appendChild(counter);
    ta.addEventListener('input', function () {
      counter.textContent = ta.value.length + ' / ' + maxLen + ' caractères';
      counter.classList.toggle('text-danger', ta.value.length >= maxLen);
    });
  });

  /* ─── Tooltip Bootstrap (activation globale) ─── */
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  /* ─── Filtre côté client sur les tableaux ─── */
  document.querySelectorAll('[data-table-search]').forEach(function (input) {
    var tableId = input.getAttribute('data-table-search');
    var tableBody = document.querySelector('#' + tableId + ' tbody');
    if (!tableBody) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      tableBody.querySelectorAll('tr').forEach(function (row) {
        row.style.display = (row.textContent.toLowerCase().includes(q)) ? '' : 'none';
      });
    });
  });

  /* ─── Indicateur de chargement sur les boutons submit ─── */
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('[type="submit"]:not([data-no-spinner])');
      if (btn && !btn.disabled) {
        var orig = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Traitement…';
        /* Rétablir si la page ne change pas (ex: erreur de validation) */
        setTimeout(function () {
          btn.disabled = false;
          btn.innerHTML = orig;
        }, 8000);
      }
    });
  });

  /* ─── Validation client champs obligatoires ─── */
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      var invalid = false;
      form.querySelectorAll('[required]').forEach(function (field) {
        if (!field.value.trim()) {
          field.classList.add('is-invalid');
          if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('invalid-feedback')) {
            var msg = document.createElement('div');
            msg.className = 'invalid-feedback';
            msg.textContent = 'Ce champ est obligatoire.';
            field.after(msg);
          }
          invalid = true;
        } else {
          field.classList.remove('is-invalid');
          field.classList.add('is-valid');
        }
      });
      if (invalid) e.preventDefault();
    });
    /* Nettoyer la classe is-valid/invalid à la saisie */
    form.querySelectorAll('input, select, textarea').forEach(function (f) {
      f.addEventListener('input', function () {
        f.classList.remove('is-invalid', 'is-valid');
      });
    });
  });

});

/* ─── Fonctions GPS globales ─────────────────────────────── */
function vsGetGPS(latFieldId, lonFieldId, btnEl) {
  if (!navigator.geolocation) {
    alert("La géolocalisation n'est pas disponible sur cet appareil.");
    return;
  }
  if (btnEl) { btnEl.disabled = true; btnEl.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Localisation…'; }
  navigator.geolocation.getCurrentPosition(
    function (pos) {
      var latField = document.getElementById(latFieldId);
      var lonField = document.getElementById(lonFieldId);
      if (latField) latField.value = pos.coords.latitude.toFixed(6);
      if (lonField) lonField.value = pos.coords.longitude.toFixed(6);
      if (btnEl) { btnEl.disabled = false; btnEl.innerHTML = '<i class="bi bi-crosshair me-1"></i>GPS auto'; }
      if (latField) latField.dispatchEvent(new Event('input'));
    },
    function () {
      if (btnEl) { btnEl.disabled = false; btnEl.innerHTML = '<i class="bi bi-crosshair me-1"></i>GPS auto'; }
      alert("Impossible d'obtenir la position. Vérifiez les autorisations du navigateur.");
    },
    { timeout: 8000, enableHighAccuracy: true }
  );
}

/* ─── Formatage superficie ──────────────────────────────── */
function formatSuperficie(ha) {
  if (ha >= 10000) return (ha / 10000).toFixed(1) + ' km²';
  return ha.toFixed(0) + ' ha';
}
