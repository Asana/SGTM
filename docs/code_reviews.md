# How SGTM works

This is an overview of SGTM's functionality.

### Creating the Pull Request

Each Pull Request in GitHub maps to a single Asana task.

The assignee of the task is the individual responsible for actioning on the Pull Request. Since the sync is one-way (GitHub → Asana), no fields should ever be changed directly in Asana as they'll not be propagated to GitHub.

Field mapping, GitHub to Asana:

| GitHub                                            | Asana                                                        |
| :------------------------------------------------ | :----------------------------------------------------------- |
| PR author                                         | follower in Asana task                                       |
| PR description                                    | description in Asana task                                    |
| PR reviewers                                      | followers in Asana task. Can approve or request changes      |
| PR assignee                                       | assignee in Asana task                                       |
| PR comment                                        | comment in Asana task. Comes from bot, but `@-mentions` comment author in Asana |
| PR review                                         | comment in Asana task. Comes from bot, but `@-mentions` review author in Asana |
| PR participants (author + reviewers + commenters) | followers in Asana task                                      |
| PR status (open/closed/merged)                    | "Status" custom field in Asana task
| PR build status (pending/success/failure)         | "Build" custom field in Asana task

#### How a GitHub Pull Request looks like

![GitHub Pull Request](/docs/github_pr.png)

#### ... and how it's reflected in Asana

![Asana task](/docs/asana_task.png)

A sublety that exists in this flow is the difference between the assignee and reviewers.

* When the assignee is the author of the Pull Request, the action required from them is likely to change the code or address concerns others have raised
* When the assignee is not the author of the Pull Request, then they're the "main reviewer". Although other GitHub reviewers can review the code, the assignee is the one ultimately responsible for ensuring that the code gets reviewed.

### Reviewing the Pull Request before merge

If you're a reviewer of a Pull Request and want to review the code before it gets merged, you should leave a [GitHub review](https://help.github.com/articles/about-pull-request-reviews/) on the Pull Request.

* An approval will tell the author that code is ready to be merged
* Requesting changes will prevent the task from being completed until a reviewer approves the Pull Request
* **Reviews that aren't approval or changes requested don't count as SGTM reviews**

SGTM detects reviews and reassigns the Pull Request (and consequently the corresponding Asana task) back to the author after a review is left — reviewers don't need to do that themselves!

### Addressing reviews before merge

If reviewers requested changes on your Pull Request, you'll likely need to push new code/reply to their comments in GitHub.

As the author, once you've determined that the Pull Request should be ready for review again, you should reassign it back to the main reviewer **[in the GitHub interface](https://help.github.com/articles/assigning-issues-and-pull-requests-to-other-github-users/)**. That involves adding the main reviewer and removing yourself as assignee.

If the last review (approval or changes requested) left by a reviewer in a Pull Request before it was merged was an approval, then the synced task will be closed after the Pull Request is merged. If the last review requested changes and the Pull Request was still merged, the task is left open so the author can address changes after merging.

### Reviewing the Pull Request after merge

The last paragraph explained in what scenarios a task gets completed after the Pull Request is merged. In all other scenarios, the task is kept open for a post-commit review.

Reviews made after the Pull Request is merged must be in the form of GitHub comments.

Approvals are comments that contain one of the following expressions: `SGTM`, `looks good`, `look good`, `looks great`, `look great`, `+1`, `:+1:`, `shipit` or `👍`. Detecting those expressions is done in a case-insensitive way, so `sgtm` and `THIS LOOKS GOOD!` also works. See [`_is_approval_comment_body`](/src/github/logic.py) for the latest regular expression whih represents an approval comment.

The Asana task remains open until the Pull Request is approved by a reviewer.

### Addressing reviews after merge

It isn't possible to add commits to a merged Pull Request. In the event your reviewer isn't satisfied with the Pull Request you merged, you should open a new Pull Request with changes, comment in the old PR with a link to the new Pull Request and ask your reviewer to approve the old PR so that the task gets completed.

### Flowchart

![Flowchart](/docs/state_transitions.png)

*[flowchart source](https://www.draw.io/?lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=Pull%20Request%20state%20transitions#R1VnLcqM4FP0aqmYWnULIELxs5zWL7qqupKtmeinDNWgCiBEitvvrRwLxsnAmGduQ9sIWV0KPo6N77pUtfJPuHjjJ468shMRy7HBn4VvLcdAC2%2FJHWfa15dp1a0PEaagbdYYn%2BhO0Ub8XlTSEYtBQMJYImg%2BNAcsyCMTARjhn22GzDUuGo%2BYkAsPwFJDEtP5JQxHXVt%2B57ux%2FAI3iZmTkLeuaNQmeI87KTI9nOXhTferqlDR96YUWMQnZtmfCdxa%2B4YyJupTubiBR2Daw1e%2FdH6lt580hE295QU%2B7EPtm6RBKJPQj4yJmEctIctdZV9XyQHVgy6dYpIksIlmEHRV%2FKfOVq59%2BNDWZ4PtelXr8oTv4G4TYawqQUjBp6sb9wliu%2BzCXpldbsJIHevaOJgvhEehWuDapdfVe03A8AEtBTkY24JAQQV%2BGDCCaSFHbrgNTFjSe49g63jnBfR9MB6v9P7ghPBFO%2BPoiJOxRsGbd5Ahidyqm1V28kKTUnX4rqwaP8E8JhVBNC%2FnFcsgkZodoD7HcxlTAU06qhW2lfx%2FiWwjOnluvKJe32tAkuWEJ41VvOHTBDxdty16N76yx5712lF%2BAC9hZrx1TXYsRvtKaojXG1S512zlsZGtb3HPWC%2Ft0wBudurTfPKtvxCZDF3P5Rmww9hFeKGyBV6OpoiLsIY2PEhf9N3HPQTp7MaAcGuOcM8I57xycQwZmexkj%2FXo8XJg8dOfiIVoYoGbsEpiiE%2BXo%2FZii2QIfdJGocgYE%2FbkQbHzI67SUXksMseJQ0J9kXTVQMOaMZqKah7uy3FtpIQmNMmkIJBbS2eKV8n5UZj6fdUVKw7DakISsIVm1%2BUxPx3VGMwrs8ohPbXM1PTurn%2B%2BM%2BdpP9hVaXA8l%2FpOm9Jvx1r1%2FUzD0mrDNpgBhbEg7iTftkek5bpnyx1q%2BKiUjec6ZnKdUskcL35sCFrN0XRbTiFcjIBrM8YDJM8WrjaJO8gnOL6hUrukTvLlcgmvQTVJKx%2FUpyAm%2BFtdPFB459kFMjpeuwTF%2FhGL4DAzzDIC%2Bk%2BJZWuTeKZCChBWXT34I%2BJtgLPnxAh%2FWR5zmu4E%2BiENdNGUcetZrjQ9wZ4RGEiM0X0RqpkYf7qB7zSQbKfGnO%2BboMrdFlxUS9JGUBJlS0ku%2BA5amkFUek2V14KL2VW6rHDVrYxqieoRdLiPOglYNf%2Fvy8P2r5cjhbevetpb31hJZ%2Fu3vs7PVXXpDUfIn9JYtG85D18YnooFHnOB6s8mFjJv1KbIh9xJH%2FtR88hwITnbH3gzeO%2FOfS7k0deLzsoirxCVlHCoPEKofuf769M99fO2h2IxeuqELHV88ebAz9cHGx6RpiltgU4ksx0vUpUaRK7HxIlWuJOggiq8kiZWi4%2BsaaBb1YqS6HzmFflensXkY%2FneYj9x2GKgf5XejRhPcKcvH7q%2Fl%2Bsqj%2B%2F8e3%2F0L)*
