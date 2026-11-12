# nav-test: sidebar experiment 3

Property ids (Unity 6000.3 StylePropertyId; flex-direction and position confirmed in game):
131083 flex-direction, 131087 height, 131089 left, 131091 margin-left, 131099 padding-left,
131102 position, 131104 top, 131105 width.

Experiment 2 result: `:root { padding-left }` had no effect; the menu went off-screen to the left.

1. styles/rules.json: new rule `.base-layer-content { margin-left: 200px }`. That class is the content
   root of Portal, Squad, Training, Club, Recruitment, Nation, International squad, National pool.
2. layout.json: MenuBar button groups: column, absolute, 200px wide, left -170px, top 90px.
