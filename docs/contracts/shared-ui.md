# Shared UI v0.1 — branch proposal

Owner: Syed Arhan. Implemented on arhan/shared-ui for Abbas's review; not yet integrated
or jointly approved. Uses the existing Django template/session/static infrastructure.
No added dependency, schema, endpoint, global setting or authorization change.

## Integration

Extend templates/base.html. Supported blocks: title, content, navigation, extra_head,
extra_scripts. Navigation extends the existing Home link; add only implemented routes,
with the domain's role visibility check and aria-current="page" for the active route.
The current Administration link requires an authenticated active ADMIN with is_staff.
Visibility never replaces accounts.permissions checks in trusted views/services.

CSS lives at core/static/brightloop/app.css, discovered by the already installed core
app. This deliberately avoids a global STATICFILES_DIRS change for a root static/
directory. Syed owns this asset and templates/base.html and templates/components/.
The home template is the B1 replacement explicitly assigned to Syed in FOUNDATION.md.
core/test_ui.py contains Syed's UI tests, separate from Abbas's platform tests.

Use the panel, button/button--primary, badge, notice, form-field, table-scroll,
data-table, amount and empty-state classes. Success/warning/error badge modifiers
control presentation only; feature owners supply the actual status text. Do not
encode status-to-style business decisions in CSS. Color is supplementary to text.

For Django forms include components/form_fields.html with form=form. Feature templates
own the form element, method/action, CSRF token, submit control, multipart encoding when
needed, and server validation. The partial renders bound input, field/help/error IDs,
non-field errors and hidden-field errors through Django's as_field_group rendering.
Never mark user-supplied content safe. Use a fieldset/legend for grouped controls.

Include components/empty_state.html with empty_title and optional empty_description.
Messages use the existing Django messages context processor and a status live region.
For asynchronous loading use role="status" and descriptive visible text; on failure
use the notice--error style and an actual retry action provided by the feature.
No asynchronous data views are implemented by this change.

Wrap wide tables in table-scroll with tabindex="0", role="region" and an accessible
label. Supply a caption and scope="col" headers. Amount cells use amount. Feature owners
provide server pagination and filters; this shell does not invent a pagination API.

## Review and compatibility

Only the implemented Home/admin routes are linked. No financial totals or fake activity
are shown. The UI is responsive without JavaScript and requires no remote fonts/assets.
Print CSS removes navigation; the actual invoice print layout remains B4 work.
Review desktop/mobile rendering and integrate Abbas's next auth screen with these
primitives before declaring the shared UI interface accepted. Revert these UI files to
restore the prior home screen; there is no data migration or database rollback.
