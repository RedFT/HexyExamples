# Hexy Example

This repo contains a graphical example of how someone might use [`hexy`](https://github.com/redft/hexy).

#### Running the example

```bash
git clone http://github.com/redft/hexyexamples
cd hexyexamples
pip install -r requirements.txt # If you're not using a virtual environment, you might need to use sudo.
python example.py
```

The example app just shows off some features of the library. To play around you can:

```
- right click to change the hex selection type. 
- scroll up and down to change the radius of selection when selection type is ring or disk.
- left click to change the starting point of the line when selection type is a line.
- When selection type is spiral, the center is the origin. Where you clik will be the start
  point for the spiral, and your mouse position is the end point.
```
