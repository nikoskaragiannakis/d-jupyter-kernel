from ipykernel.kernelapp import IPKernelApp
from .kernel import DKernel
IPKernelApp.launch_instance(kernel_class=DKernel)
