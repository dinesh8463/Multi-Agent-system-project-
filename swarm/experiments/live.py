"""Optional Tk playback window, isolated from the default Agg backend."""
import sys
import tkinter as tk
from PIL import Image, ImageTk, ImageSequence


def main():
    root = tk.Tk()
    root.title('Drone swarm mission playback')
    animation = Image.open(sys.argv[1])
    frames = [ImageTk.PhotoImage(frame.convert('RGB')) for frame in ImageSequence.Iterator(animation)]
    label = tk.Label(root)
    label.pack()
    def update(index=0):
        label.configure(image=frames[index])
        root.after(125, update, (index+1) % len(frames))
    update()
    root.mainloop()


if __name__ == '__main__':
    main()
