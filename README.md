# Minimal Jupyter kernel wrapper for D language

## Introductions
Say hello to the first Jupyter kernel wrapper for D language!

Currently, you need to run the whole code in the same cell in order for it to be executed successfully. 
This implementation is far from efficient, but it is a start.

At the moment I am trying to integrate [drepl](https://github.com/dlang-community/drepl) with the help of [autowrap](https://github.com/kaleidicassociates/autowrap).
I will try to update it on my spare time, so don't expect things happening very fast here.

Feel free to give feedback and/or help improve it.


## Manual installation
This works on Linux. I haven't tried it yet on MacOS or Windows.


 * Make sure you have the following requirements installed:
  * dmd
  * jupyter
  * python 3
  * pip

### Step-by-step:
 * clone the repo
 * `cd d-jupyter-kernel` inside the repo's root directory
 * `python setup.py install`
 * `python d_jupyter_kernel/install.py`. Enjoy!
 * `jupyter-notebook`. Enjoy!


## Sample notebook
![Sample notebook](D_kernel_example.png?raw=true "Example of notebook")

## License
[MIT](LICENSE)
