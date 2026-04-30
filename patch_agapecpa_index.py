#!/usr/bin/env python3
"""
Run this script from your project root to patch agapecpa.com/index.html.
It replaces the broken Formidable form with a native Netlify form.

Usage:
    python3 patch_agapecpa_index.py
"""

import re
import sys
import shutil
from pathlib import Path

TARGET = Path("agapecpa.com/index.html")

if not TARGET.exists():
    print(f"ERROR: {TARGET} not found. Run this from your project root.")
    sys.exit(1)

# Backup original
backup = TARGET.with_suffix(".html.bak")
shutil.copy(TARGET, backup)
print(f"Backed up original to {backup}")

html = TARGET.read_text(encoding="utf-8")

# ── New Netlify form ──────────────────────────────────────────────────────────
NEW_FORM = """<div class="frm_forms  with_frm_style frm_style_formidable-style" id="frm_form_2_container" >
<form name="contact-agape-home" method="POST" data-netlify="true" netlify-honeypot="bot-field">
  <input type="hidden" name="form-name" value="contact-agape-home" />
  <p style="display:none"><label>Don't fill this out: <input name="bot-field" /></label></p>
  <div class="frm_form_fields ">
    <fieldset>
      <legend class="frm_screen_reader">免費諮詢</legend>
      <div class="frm_fields_container" style="display:flex; flex-wrap:wrap; gap:0 2%;">

        <div id="frm_field_6_container" class="frm_form_field form-field frm_required_field frm_top_container frm_third frm_first" style="flex:1 1 200px; min-width:200px; margin-bottom:16px;">
          <label for="field_name_h" class="frm_primary_label">您的姓名
            <span class="frm_required">*</span>
          </label>
          <input type="text" id="field_name_h" name="name" required aria-required="true"
                 style="width:100%; padding:12px 15px; border:1px solid #ededed; border-bottom-width:4px; border-style:solid; border-radius:3px; background:#fff;" />
        </div>

        <div id="frm_field_8_container" class="frm_form_field form-field frm_required_field frm_top_container frm_third" style="flex:1 1 200px; min-width:200px; margin-bottom:16px;">
          <label for="field_email_h" class="frm_primary_label">電子郵件
            <span class="frm_required">*</span>
          </label>
          <input type="email" id="field_email_h" name="email" required aria-required="true"
                 style="width:100%; padding:12px 15px; border:1px solid #ededed; border-bottom-width:4px; border-style:solid; border-radius:3px; background:#fff;" />
        </div>

        <div id="frm_field_11_container" class="frm_form_field form-field frm_required_field frm_top_container frm_third" style="flex:1 1 200px; min-width:200px; margin-bottom:16px;">
          <label for="field_phone_h" class="frm_primary_label">電話
            <span class="frm_required">*</span>
          </label>
          <input type="tel" id="field_phone_h" name="phone" required aria-required="true"
                 style="width:100%; padding:12px 15px; border:1px solid #ededed; border-bottom-width:4px; border-style:solid; border-radius:3px; background:#fff;" />
        </div>

        <div id="frm_field_9_container" class="frm_form_field form-field frm_required_field frm_top_container frm_full" style="width:100%; margin-bottom:16px;">
          <label for="field_subject_h" class="frm_primary_label">主題
            <span class="frm_required">*</span>
          </label>
          <input type="text" id="field_subject_h" name="subject" required aria-required="true"
                 style="width:100%; padding:12px 15px; border:1px solid #ededed; border-bottom-width:4px; border-style:solid; border-radius:3px; background:#fff;" />
        </div>

        <div id="frm_field_10_container" class="frm_form_field form-field frm_required_field frm_top_container frm_full" style="width:100%; margin-bottom:16px;">
          <label for="field_message_h" class="frm_primary_label">內容
            <span class="frm_required">*</span>
          </label>
          <textarea id="field_message_h" name="message" rows="5" required aria-required="true"
                    style="width:100%; padding:12px 15px; border:1px solid #ededed; border-bottom-width:4px; border-style:solid; border-radius:3px; background:#fff;"></textarea>
        </div>

        <div class="frm_submit" style="width:100%;">
          <button class="frm_button_submit frm_final_submit" type="submit" formnovalidate="formnovalidate">Submit</button>
        </div>

      </div>
    </fieldset>
  </div>
</form>
</div>"""

# ── Replace the old Formidable form block ─────────────────────────────────────
# Match from the frm_forms div open tag to its closing </div>
pattern = re.compile(
    r'<div class="frm_forms\s+with_frm_style frm_style_formidable-style"[^>]*id="frm_form_2_container"[^>]*>.*?</form>\s*</div>',
    re.DOTALL
)

count = len(pattern.findall(html))
if count == 0:
    print("ERROR: Could not find the Formidable form block.")
    print("The HTML structure may have changed. Check the file manually.")
    sys.exit(1)

patched = pattern.sub(NEW_FORM, html, count=1)
TARGET.write_text(patched, encoding="utf-8")
print(f"✅ Successfully patched {TARGET}")
print(f"   Replaced {count} form block(s)")
print()
print("Next steps:")
print("  1. git add agapecpa.com/index.html")
print('  2. git commit -m "Add Netlify form to homepage free consultation section"')
print("  3. git push")
print("  4. Netlify Dashboard → Deploys → Clear cache and deploy site")
print("  5. Form submissions appear in Forms tab as 'contact-agape-home'")