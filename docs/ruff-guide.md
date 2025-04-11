## Why should i use pre-commit?
Pre-commit에 대해서 이해하려면, 우선 "이걸 왜 사용해야 하는가?"를 이야기할 필요가 있다. 가령 대규모 프로젝트를 한다고 생각해보자. 그런데 만약 "일관된 규칙"이 없다면, 개발자(contributor)들은 각자 다른 방식으로 코드를 작성할 것이며, 따라서 줄 간격이 불규칙 해지므로 가독성이 저하된다는 등의 문제가 발생할 수 있다.

이를 해결하기 위해 등장한 개념이 **일관된 규칙**을 적용하는, pre-commit이다. `Ruff`는 전 세계에서 가장 유명한 `python` pre-commit 도구다.

## 🧐 How to use??

```bash
# Initial Setting
pre-commit install

# Run with pre-commit-hooks
pre-commit run --all-files
```

## 📝 설정 파일 (.pre-commit-config.yaml)

```yaml
exclude: |
    (?x)(
        # Docs
        ^.*\.md$|
        ^docs/|

        # Cache files
        ^.pytest_cache/|
        ^__pycache__/|

        ^\.env|
        ^\.vscode/
    )
repos:
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.9.9
  hooks:
    - id: ruff
      args: [--fix]
      types_or: [python, jupyter]

- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v5.0.0
  hooks:
    - id: check-added-large-files
    - id: check-merge-conflict
    - id: check-toml
    - id: check-yaml
    - id: end-of-file-fixer
    - id: mixed-line-ending
      args: [--fix=lf]
    - id: trailing-whitespace
```

## Hook 설명
### Pre-commit-hooks
기본적인 파일 검사와 포맷팅을 수행합니다.

- `trailing-whitespace`: 줄 끝의 불필요한 공백 제거
- `end-of-file-fixer`: 파일 끝에 newline 추가
- `check-yaml`: YAML 파일 문법 검사
- `check-toml`: TOML 파일 문법 검사
- `debug-statements`: 디버그 구문(pdb, ipdb 등) 검사
- `check-added-large-files`: 큰 파일(ex. checkpoint)의 실수 커밋 방지

### Git Hooks 자동 실행

commit 시 자동으로 실행됩니다:

```bash
git commit -m "메시지"
# pre-commit hooks 자동 실행
```

### See also
- [Blog post : pre-commit](https://until.blog/@namgyu-youn/pre-commit%EC%9D%B4%EB%9E%80-%EB%AC%B4%EC%97%87%EC%9D%B8%EA%B0%80-)
- [Ruff docs](https://docs.astral.sh/ruff/)
- [UV](https://docs.astral.sh/uv/guides/projects/#creating-a-new-project) : Fast and compact python package tool (better than Poetry)
