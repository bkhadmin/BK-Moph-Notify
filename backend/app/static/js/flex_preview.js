function renderFlexPreview(textareaId, previewId){
  try{
    const json=JSON.parse(document.getElementById(textareaId).value)
    const body=json.body?.contents||[]
    let html='<div class="flex-card">'
    body.forEach(c=>{
      if(c.type==='text'){
        html+=`<div class="flex-text">${c.text}</div>`
      }
    })
    html+='</div>'
    document.getElementById(previewId).innerHTML=html
  }catch(e){
    document.getElementById(previewId).innerHTML='<div class="muted">invalid json</div>'
  }
}
