# Minimal Jupyter kernel wrapper for D language

## Introductions
Say hello to the first Jupyter kernel wrapper for D language!

Currently, you can:
 * import modules, 
 * define functions, and
 * try out commands 

in different cells, without the need of a `main` function.

The implementation is far from efficient, but it is a start.

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
 * `pip install -e .` inside the repo's root directory
 * `python setup.py install`
 * `jupyter-notebook`. Enjoy!


## Sample notebook
![Sample notebook](D_kernel_example.png?raw=true "Example of notebook")

## License
[MIT](LICENSE)
