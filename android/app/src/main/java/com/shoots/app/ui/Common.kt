package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shoots.app.Amber
import com.shoots.app.FindingRed
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.InkRaised
import com.shoots.app.MutedWhite
import com.shoots.app.WarmWhite
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun ScreenTitle(eyebrow: String, title: String, supporting: String = "") {
    Text(eyebrow.uppercase(), color = Amber, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    Spacer(Modifier.height(8.dp))
    Text(title, color = WarmWhite, fontSize = 30.sp, lineHeight = 35.sp, fontWeight = FontWeight.Bold)
    if (supporting.isNotBlank()) {
        Spacer(Modifier.height(8.dp))
        Text(supporting, color = MutedWhite, fontSize = 15.sp, lineHeight = 21.sp)
    }
}

@Composable
fun SectionTitle(title: String, aside: String = "") {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(title, color = WarmWhite, fontSize = 17.sp, fontWeight = FontWeight.SemiBold)
        if (aside.isNotBlank()) Text(aside, color = MutedWhite, fontSize = 11.sp)
    }
}

@Composable
fun InkCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val clickable = if (onClick == null) modifier else modifier.clickable(onClick = onClick)
    Column(
        clickable
            .fillMaxWidth()
            .background(InkRaised, RoundedCornerShape(18.dp))
            .border(1.dp, Hairline, RoundedCornerShape(18.dp))
            .padding(18.dp),
        content = content,
    )
}

@Composable
fun PrimaryAction(label: String, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = Amber,
            contentColor = Ink,
            disabledContainerColor = Hairline,
            disabledContentColor = MutedWhite,
        ),
    ) { Text(label, fontWeight = FontWeight.Bold) }
}

@Composable
fun SecondaryAction(label: String, danger: Boolean = false, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().height(50.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = if (danger) FindingRed else WarmWhite),
    ) { Text(label, fontWeight = FontWeight.SemiBold) }
}

@Composable
fun StatusPill(text: String, amber: Boolean = false, red: Boolean = false) {
    val colour = when {
        red -> FindingRed
        amber -> Amber
        else -> MutedWhite
    }
    Text(
        text.uppercase(),
        color = colour,
        fontSize = 10.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .background(colour.copy(alpha = 0.12f), RoundedCornerShape(99.dp))
            .padding(horizontal = 9.dp, vertical = 5.dp),
    )
}

@Composable
fun MessageBanner(message: String, error: Boolean, onDismiss: () -> Unit) {
    if (message.isBlank()) return
    val colour = if (error) FindingRed else Amber
    Row(
        Modifier
            .fillMaxWidth()
            .background(colour.copy(alpha = 0.1f), RoundedCornerShape(14.dp))
            .border(1.dp, colour.copy(alpha = 0.45f), RoundedCornerShape(14.dp))
            .clickable(onClick = onDismiss)
            .padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(message, color = WarmWhite, fontSize = 13.sp, lineHeight = 18.sp, modifier = Modifier.weight(1f))
        Text("×", color = colour, fontSize = 18.sp, modifier = Modifier.padding(start = 10.dp))
    }
}

@Composable
fun LabelValue(label: String, value: String, valueColour: Color = WarmWhite) {
    if (value.isBlank()) return
    Text(label.uppercase(), color = MutedWhite, fontSize = 10.sp, fontWeight = FontWeight.Bold)
    Spacer(Modifier.height(3.dp))
    Text(value, color = valueColour, fontSize = 14.sp, lineHeight = 20.sp)
}

fun displayTime(value: String): String = runCatching {
    DateTimeFormatter.ofPattern("d MMM, HH:mm")
        .withZone(ZoneId.systemDefault())
        .format(Instant.parse(value))
}.getOrDefault(value.take(16).replace('T', ' '))
