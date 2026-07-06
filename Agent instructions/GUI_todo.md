# GUI task list

## Tasks:

### General GUI

1. switch the "Direct Control" and "Mask Generation" tab locations. I want mask generation to be the first to open.

### Mask Generation GUI

2. Currently there are two control panels: "Target and Algorithm", "TEM/HG Target". Instead, I want three panels:

    a."Algorithm": will have algorithm selection, iteration seed. there will be an "Apply" button also that makes the frame regenerate.

    b. "Target": will have a dropdown with two options (in the future there will be more), Each choise will show a different set of buttons:
    - "TEM/HG" option will show the relevent fields
    - "from file" will show buttons for loading image (like the current load png button)
  
    b. "Control" This is where all the toggles will be, as well as the save BMP button and Generat mask button. Also, add two new paramaters: offset x and offset y. these add a slope (mod 2pi) to the wfc, and can be used to apply an offset to the projected image.

In addiotion, every change in the target/control options,as well as pressing the apply button in algorithm, will automaticaly regenerate the mask, and then send to the slm.
