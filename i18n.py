from bpy.app.translations import contexts

datas = {
    'Surface Tools': {
        'zh': '曲面工具',
    },
    'Generate Surface': {
        'zh': '生成曲面',
    },
    'Sweep1': {
        'context': contexts.operator_default,
        'zh': '单轨扫掠',
    },
    'Sweep2': {
        'context': contexts.operator_default,
        'zh': '双轨扫掠',
    },
}

langs = {}

for name in datas:
    context = datas[name].pop('context', None)
    if not context:
        context = contexts.default
    datas[name]["en"] = name
    for lang in datas[name]:
        if lang not in langs:
            langs[lang] = {}
        key = (context, name)
        langs[lang][key] = datas[name][lang]
