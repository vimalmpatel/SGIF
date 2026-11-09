# Security Policy

## Operating boundary

SGIF is a defensive framework for small renewable-energy operators. The
current Ansible examples target dedicated Debian/Ubuntu support servers only.
They must not be run against inverters, turbines, relays, plant controllers,
or any other OT device or network.

## Change safety

- Keep role enable flags off unless a change is approved for the exact host.
- Test in a disposable or non-production environment first.
- Review the rendered diff and Ansible check-mode output where supported.
- Confirm console or out-of-band recovery access before SSH or firewall work.
- Maintain a tested backup and rollback plan.
- Apply one control group at a time and verify service health after each change.
- Do not store credentials, private keys, real inventories, or secrets in Git.
- Never treat a successful playbook run as proof of compliance or safety.

## CI and deployment

Pull-request CI runs tests and syntax checks; it does not connect to site
systems. The manual deployment workflow is currently a syntax preflight only.
Any future remote deployment requires a separately reviewed target model,
protected environment, explicit authorization, and operator-controlled
rollback.