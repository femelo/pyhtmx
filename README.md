# PyHTMX


PyHTMX is a dead simple library to generate HTMX code in Python.

Inspired by this StackOverflow thread on [how to generate HTML with XML](https://stackoverflow.com/questions/70408116/generate-html-xml-in-python).


## Features

- Outputs indented code
- Outputs subtrees for the generated DOM
- Children elements and content can be provided as lists
- Building based on nested constructors or `with` statements


## Installing

```bash
  $ python3 -m pip install pyhtmx-lib
```

## Examples

First, an example based on nesting constructors:

```python
  from pyhtmx import *

  html = Html(
    [
      Head(
        [
          Title('My Website'),
          Script(src="https://unpkg.com/htmx.org@2.0.3"),
        ]
      ),
      Body(
        [
          Header(
            [
              Img(src='/path/to/logo.png', _id="logo"),
              Nav(
                Ul(
                  [
                    Li(
                      "First item.",
                      hx_post="/first-item-clicked",
                      hx_trigger="click",
                      hx_target="#container-div",
                      hx_swap="innerHTML",
                    ),
                    Li("Second item."),
                    Li("Third item.")
                  ]
                ),
              ),
            ]
          ),
          Div(
            'Content here',
            _id="container-div",
          ),
          Footer([Hr(), 'Copyright 2024']),
        ]
      ),
    ]
  )

html.dump()

```

The example results in the following output:

```html
<html>
  <head>
    <title>My Website</title>
    <script src="https://unpkg.com/htmx.org@2.0.3" />
  </head>
  <body>
    <header>
      <img src="/path/to/logo.png" id="logo" />
      <nav>
        <ul>
          <li hx-post="/first-item-clicked" hx-trigger="click" hx-target="#container-div" hx-swap="innerHTML">First item.</li>
          <li>Second item.</li>
          <li>Third item.</li>
        </ul>
      </nav>
    </header>
    <div id="container-div">Content here</div>
    <footer>
      <hr />
      <span>Copyright 2024</span>
    </footer>
  </body>
</html>

```

Now an example based on contexts defined with the `with` statement,

```python
with Div(_class="btn-primary") as div:
  with A(href="/link/to/another/site"):
    with P("This is the first paragraph.", style="color: blue"):
      pass
  with P("Yet another paragraph.", style="color: red"):
    pass

div.dump()

```

which results in

```html
<div class="btn-primary">
  <a href="/link/to/another/site">
    <p style="color: blue">This is the first paragraph.</p>
  </a>
  <p style="color: red">Yet another paragraph.</p>
</div>

```

Related projects
----------------

* https://github.com/cenkalti/pyhtml
* https://github.com/COMP1010UNSW/pyhtml-enhanced
