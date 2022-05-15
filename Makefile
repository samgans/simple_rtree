base_python = python3
venv_dirname = .venv
req_prod = requirements.txt
req_dev = requirements

interpreter_path = ${venv_dirname}/bin/${base_python}

${interpreter_path}:
	${base_python} -m venv ${venv_dirname}
	${interpreter_path} -m pip install pip-tools

requirements.txt: ${interpreter_path} requirements.in
	${interpreter_path} -m piptools compile requirements.in --output-file requirements.txt

requirements_dev.txt: ${interpreter_path} requirements_dev.in
	${interpreter_path} -m piptools compile requirements_dev.in --output-file requirements_dev.txt

.PHONY: setup_venv
setup_venv: ${interpreter_path}

.PHONY: compile_req
compile_req: requirements.txt

.PHONY: dev_compile_req
dev_compile_req: requirements_dev.txt

.PHONY: install_req
install_req: ${interpreter_path} requirements.txt
	${interpreter_path} -m pip install -r requirements.txt

.PHONY: dev_install_req
dev_install_req: ${interpreter_path} requirements_dev.txt
	${interpreter_path} -m pip install -r requirements_dev.txt
